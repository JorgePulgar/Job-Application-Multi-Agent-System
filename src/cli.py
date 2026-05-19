"""Command-line interface entry point for the job-agent system.

Run with:  python -m src.cli --help
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from alembic.config import Config as AlembicConfig
from sqlalchemy import select

from alembic import command as alembic_command
from src.agents.offer_filter import OfferFilter
from src.db import Offer, OfferEstado, get_session
from src.services.azure_openai import AzureOpenAIClient
from src.services.profiles import load_profile, upsert_user_row
from src.services.scrape_runner import ALL_PLATFORMS, ScrapeRunSummary, run_scrape

# ---------------------------------------------------------------------------
# Shared context object passed to every subcommand via @click.pass_obj
# ---------------------------------------------------------------------------


class AppContext:
    """Runtime options shared across all subcommands."""

    def __init__(
        self,
        log_level: str,
        config_path: Path,
        dry_run: bool,
    ) -> None:
        self.log_level = log_level
        self.config_path = config_path
        self.dry_run = dry_run


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--log-level",
    default="INFO",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging verbosity.",
)
@click.option(
    "--config-path",
    default="config/users",
    show_default=True,
    type=click.Path(),
    help="Directory containing user YAML profiles.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Run pipeline logic without writing to the DB or calling external APIs.",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str, config_path: str, dry_run: bool) -> None:
    """Job-agent: automated job application assistant."""
    ctx.ensure_object(dict)
    ctx.obj = AppContext(
        log_level=log_level.upper(),
        config_path=Path(config_path),
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# profile group (real — Task 05)
# ---------------------------------------------------------------------------


@cli.group()
def profile() -> None:
    """Manage user profiles."""


@profile.command("load")
@click.option("--user", required=True, help="Username matching <config-path>/<user>.yaml")
@click.pass_obj
def profile_load(obj: AppContext, user: str) -> None:
    """Validate a user YAML and upsert the corresponding users table row."""
    p = load_profile(user)
    upsert_user_row(p)
    roles = ", ".join(p.target_roles[:3])
    click.echo(f"OK  {p.username} ({p.nombre}) — {len(p.experiences)} exp, roles: {roles}")


# ---------------------------------------------------------------------------
# db group (real — Alembic wrappers)
# ---------------------------------------------------------------------------


@cli.group()
def db() -> None:
    """Database management commands."""


def _alembic_cfg() -> AlembicConfig:
    cfg = AlembicConfig("alembic.ini")
    return cfg


@db.command("init")
def db_init() -> None:
    """Create the database and apply all migrations (alembic upgrade head)."""
    click.echo("Initialising database …")
    alembic_command.upgrade(_alembic_cfg(), "head")
    click.echo("Done.")


@db.command("migrate")
def db_migrate() -> None:
    """Apply any pending Alembic migrations (upgrade head)."""
    click.echo("Applying pending migrations …")
    alembic_command.upgrade(_alembic_cfg(), "head")
    click.echo("Done.")


# ---------------------------------------------------------------------------
# scrape (Phase 2)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--user", required=True, help="Username to scrape offers for.")
@click.option(
    "--platforms",
    default=",".join(ALL_PLATFORMS),
    show_default=True,
    help=f"Comma-separated platforms to scrape. Choices: {', '.join(ALL_PLATFORMS)}.",
)
@click.pass_obj
def scrape(obj: AppContext, user: str, platforms: str) -> None:
    """Scrape job offers from configured platforms and save new ones to the DB."""
    selected = tuple(p.strip() for p in platforms.split(",") if p.strip() in set(ALL_PLATFORMS))
    if not selected:
        click.echo(
            f"No valid platforms in '{platforms}'. Choices: {', '.join(ALL_PLATFORMS)}",
            err=True,
        )
        sys.exit(1)

    profile = load_profile(user)
    summary: ScrapeRunSummary = asyncio.run(
        run_scrape(profile, platforms=selected, dry_run=obj.dry_run)
    )

    click.echo("\n=== Scrape Summary ===")
    for platform, count in summary.per_platform.items():
        if platform in summary.errors:
            click.echo(f"  {platform}: ERROR — {summary.errors[platform][:80]}")
        else:
            click.echo(f"  {platform}: {count} raw offers")
    click.echo(f"  Dedup dropped:  {summary.dedup_dropped}")
    if summary.dry_run:
        click.echo(f"  Would write:    {summary.written} (dry-run, no DB changes)")
    else:
        click.echo(f"  Already in DB:  {summary.existing_dropped}")
        click.echo(f"  Written to DB:  {summary.written}")
    click.echo("=====================\n")


# ---------------------------------------------------------------------------
# filter (Phase 3)
# ---------------------------------------------------------------------------


async def _run_filter(
    obj: AppContext,
    username: str,
    *,
    limit: int | None,
    dry_run: bool,
) -> None:
    user_profile = load_profile(username)
    client = AzureOpenAIClient()
    agent = OfferFilter(client)

    with get_session() as session:
        # Resolve the user's DB id via the users table
        from src.db.models import User

        user_row = session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if user_row is None:
            click.echo(
                f"User '{username}' not found in DB. "
                f"Run: python -m src.cli profile load --user {username}",
                err=True,
            )
            return

        q = (
            select(Offer)
            .where(Offer.user_id == user_row.id)
            .where(Offer.estado == OfferEstado.nueva)
            .order_by(Offer.fecha_detectada.desc())
        )
        if limit is not None:
            q = q.limit(limit)

        offers = list(session.execute(q).scalars().all())

        if not offers:
            click.echo("No hay ofertas nuevas para filtrar.")
            return

        click.echo(f"Filtrando {len(offers)} oferta(s) para '{username}'…")

        summary = await agent.evaluate_batch(offers, user_profile)

        if dry_run:
            click.echo("\n=== Resultado (dry-run — sin cambios en DB) ===")
            for offer, decision in zip(offers, summary.decisions, strict=True):
                razon = decision.razon_descarte or ""
                status = "RELEVANTE" if decision.relevant else f"DESCARTADA: {razon}"
                click.echo(f"  [{offer.id}] {offer.titulo[:60]} → {status}")
            # Roll back so no changes persist
            session.rollback()
        else:
            click.echo("\n=== Resultado ===")
            for offer, decision in zip(offers, summary.decisions, strict=True):
                status = "RELEVANTE" if decision.relevant else "DESCARTADA"
                click.echo(f"  [{offer.id}] {offer.titulo[:60]} → {status}")

    click.echo("\n=== Resumen del filtrado ===")
    click.echo(f"  Relevantes:          {summary.relevant_count}")
    click.echo(f"  Descartadas:         {summary.discarded_count}")
    click.echo(f"  Short-circuit flags: {summary.red_flag_count}")
    click.echo("===========================\n")


@cli.command("filter")
@click.option("--user", required=True, help="Username whose new offers to filter.")
@click.option("--limit", default=None, type=int, help="Process at most N offers (for testing).")
@click.option(
    "--dry-run",
    "filter_dry_run",
    is_flag=True,
    default=False,
    help="Print decisions without writing to the DB.",
)
@click.pass_obj
def filter_offers(obj: AppContext, user: str, limit: int | None, filter_dry_run: bool) -> None:
    """Run the offer-filter agent on all 'nueva' offers for the given user."""
    asyncio.run(_run_filter(obj, user, limit=limit, dry_run=filter_dry_run or obj.dry_run))


# ---------------------------------------------------------------------------
# research-companies (stub — Phase 4)
# ---------------------------------------------------------------------------


@cli.command("research-companies")
@click.option("--user", required=True, help="Username whose filtered offers to research.")
@click.pass_obj
def research_companies(obj: AppContext, user: str) -> None:
    """Run the company-researcher agent for all filtered offers."""
    click.echo("not implemented (phase 4)")


# ---------------------------------------------------------------------------
# evaluate (stub — Phase 5)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--user", required=True, help="Username whose researched offers to evaluate.")
@click.pass_obj
def evaluate(obj: AppContext, user: str) -> None:
    """Run the viability-evaluator agent on researched offers."""
    click.echo("not implemented (phase 5)")


# ---------------------------------------------------------------------------
# write-drafts (stub — Phase 6)
# ---------------------------------------------------------------------------


@cli.command("write-drafts")
@click.option("--user", required=True, help="Username for whom to generate application drafts.")
@click.pass_obj
def write_drafts(obj: AppContext, user: str) -> None:
    """Run the application-writer agent for evaluated offers."""
    click.echo("not implemented (phase 6)")


# ---------------------------------------------------------------------------
# orchestrator group (stub — Phase 7)
# ---------------------------------------------------------------------------


@cli.group()
def orchestrator() -> None:
    """Full pipeline orchestration commands."""


@orchestrator.command("run")
@click.option("--user", default=None, help="Run pipeline for a single user.")
@click.option("--all-users", is_flag=True, default=False, help="Run pipeline for all users.")
@click.pass_obj
def orchestrator_run(obj: AppContext, user: str | None, all_users: bool) -> None:
    """Run the full job-hunting pipeline (scrape → filter → research → evaluate → draft)."""
    if not user and not all_users:
        click.echo("Provide --user <username> or --all-users.", err=True)
        sys.exit(1)
    click.echo("not implemented (phase 7)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
