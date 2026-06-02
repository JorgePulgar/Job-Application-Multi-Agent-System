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
from src.agents.application_writer import ApplicationWriter
from src.agents.company_researcher import CompanyResearcher
from src.agents.offer_filter import OfferFilter
from src.agents.viability_evaluator import ViabilityEvaluator
from src.db import Company, Offer, OfferEstado, get_session
from src.db.models import Evaluation, User
from src.models.evaluation import ViabilityEvaluation
from src.services import draft_persistence
from src.services.azure_openai import AzureOpenAIClient, TokenUsage, register_usage_tracker
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
# research-companies (Phase 4)
# ---------------------------------------------------------------------------


def _is_cached(session: object, name: str) -> bool:
    """Return True if a fresh dossier for *name* already exists in the DB."""
    import datetime

    from sqlalchemy.orm import Session as _Session

    assert isinstance(session, _Session)
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    row = session.execute(select(Company).where(Company.nombre == name)).scalar_one_or_none()
    return (
        row is not None
        and row.expira_en is not None
        and row.expira_en > now
        and row.dossier_json is not None
    )


async def _run_research(
    obj: AppContext,
    username: str,
    *,
    force_refresh: bool,
    limit: int | None,
) -> None:
    client = AzureOpenAIClient()

    with get_session() as session:
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
            .where(Offer.estado == OfferEstado.filtrada)
            .where(Offer.company_id.is_(None))
        )
        if limit is not None:
            q = q.limit(limit)

        offers = list(session.execute(q).scalars().all())

        if not offers:
            click.echo("No hay ofertas filtradas sin empresa investigada.")
            return

        # Deduplicate company names, preserve insertion order.
        seen_names: set[str] = set()
        unique_names: list[str] = []
        for o in offers:
            if o.empresa not in seen_names:
                seen_names.add(o.empresa)
                unique_names.append(o.empresa)

        click.echo(
            f"Investigando {len(unique_names)} empresa(s) "
            f"({len(offers)} oferta(s)) para '{username}'…"
        )

        agent = CompanyResearcher(client, session)
        researched = 0
        cache_hits = 0
        errors = 0

        for name in unique_names:
            if obj.dry_run:
                click.echo(f"  [dry-run] skip: {name}")
                continue

            was_cached = _is_cached(session, name) and not force_refresh

            try:
                dossier = await agent.research(name, force_refresh=force_refresh)
            except Exception as exc:
                click.echo(f"  ERROR researching '{name}': {exc}", err=True)
                errors += 1
                continue

            if was_cached:
                cache_hits += 1
                click.echo(f"  CACHE: {name}")
            else:
                researched += 1
                click.echo(f"  OK:    {name} ({dossier.sector}, {dossier.tamano})")

            # Link all matching offers to the company row.
            company_row = session.execute(
                select(Company).where(Company.nombre == name)
            ).scalar_one_or_none()
            if company_row is not None:
                for offer in offers:
                    if offer.empresa == name and offer.company_id is None:
                        offer.company_id = company_row.id
                        offer.estado = OfferEstado.investigada

        linked = sum(1 for o in offers if o.company_id is not None)
        click.echo("\n=== Resumen de investigación ===")
        click.echo(f"  Investigadas (nuevas): {researched}")
        click.echo(f"  Cache hits:            {cache_hits}")
        click.echo(f"  Errores:               {errors}")
        click.echo(f"  Ofertas vinculadas:    {linked}")
        click.echo("================================\n")


@cli.command("research-companies")
@click.option("--user", required=True, help="Username whose filtered offers to research.")
@click.option(
    "--force-refresh",
    is_flag=True,
    default=False,
    help="Bypass the 30-day cache and re-research all companies.",
)
@click.option("--limit", default=None, type=int, help="Process at most N companies (for testing).")
@click.pass_obj
def research_companies(obj: AppContext, user: str, force_refresh: bool, limit: int | None) -> None:
    """Research companies behind filtered offers and link them in the DB."""
    asyncio.run(_run_research(obj, user, force_refresh=force_refresh, limit=limit))


# ---------------------------------------------------------------------------
# evaluate (Phase 5)
# ---------------------------------------------------------------------------


async def _run_evaluate(
    obj: AppContext,
    username: str,
    *,
    limit: int | None,
    dry_run: bool,
) -> None:
    user_profile = load_profile(username)
    client = AzureOpenAIClient()

    with get_session() as session:
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
            .where(Offer.estado.in_([OfferEstado.investigada, OfferEstado.filtrada]))
            .where(Offer.company_id.is_not(None))
            .order_by(Offer.fecha_detectada.desc())
        )
        if limit is not None:
            q = q.limit(limit)

        offers = list(session.execute(q).scalars().all())

        if not offers:
            click.echo("No hay ofertas investigadas listas para evaluar.")
            return

        click.echo(f"Evaluando {len(offers)} oferta(s) para '{username}'…")

        agent = ViabilityEvaluator(client, session)
        counts: dict[str, int] = {"aplicar": 0, "dudar": 0, "descartar": 0, "error": 0}

        for offer in offers:
            company_row = session.execute(
                select(Company).where(Company.id == offer.company_id)
            ).scalar_one_or_none()

            if company_row is None:
                click.echo(f"  SKIP [{offer.id}] {offer.titulo[:50]} — empresa no encontrada")
                continue

            if dry_run:
                click.echo(f"  [dry-run] skip: [{offer.id}] {offer.titulo[:50]}")
                continue

            try:
                evaluation = await agent.evaluate(offer, company_row, user_profile)
                counts[evaluation.recomendacion] += 1
                click.echo(
                    f"  [{offer.id}] {offer.titulo[:50]} "
                    f"→ {evaluation.recomendacion.upper()} (score: {evaluation.score})"
                )
            except Exception as exc:
                counts["error"] += 1
                click.echo(f"  ERROR [{offer.id}] {offer.titulo[:50]}: {exc}", err=True)

        if dry_run:
            session.rollback()

    click.echo("\n=== Resumen de evaluación ===")
    click.echo(f"  Aplicar:   {counts['aplicar']}")
    click.echo(f"  Dudar:     {counts['dudar']}")
    click.echo(f"  Descartar: {counts['descartar']}")
    click.echo(f"  Errores:   {counts['error']}")
    click.echo("=============================\n")


@cli.command()
@click.option("--user", required=True, help="Username whose researched offers to evaluate.")
@click.option("--limit", default=None, type=int, help="Process at most N offers (for testing).")
@click.option(
    "--dry-run",
    "evaluate_dry_run",
    is_flag=True,
    default=False,
    help="Print plan without writing to the DB.",
)
@click.pass_obj
def evaluate(obj: AppContext, user: str, limit: int | None, evaluate_dry_run: bool) -> None:
    """Run the viability-evaluator agent on researched offers."""
    asyncio.run(_run_evaluate(obj, user, limit=limit, dry_run=evaluate_dry_run or obj.dry_run))


# ---------------------------------------------------------------------------
# write-drafts (Phase 6)
# ---------------------------------------------------------------------------


def _eval_from_row(ev: Evaluation) -> ViabilityEvaluation:
    """Reconstruct the ViabilityEvaluation pydantic model from its stored row."""
    contras = ev.contras if isinstance(ev.contras, dict) else {}
    return ViabilityEvaluation(
        score=ev.puntuacion,
        ventajas=list(ev.pros or []),
        desventajas=list(contras.get("desventajas", [])),
        red_flags_match=list(contras.get("red_flags_match", [])),
        recomendacion=ev.recomendacion,  # type: ignore[arg-type]
        reasoning=ev.razonamiento or "",
    )


async def _run_write_drafts(
    obj: AppContext,
    username: str,
    *,
    limit: int | None,
    dry_run: bool,
    recomendacion: str | None,
) -> None:
    user_profile = load_profile(username)
    client = AzureOpenAIClient()
    agent = ApplicationWriter(client)

    total_tokens = 0

    def _track(_model: str, usage: TokenUsage) -> None:
        nonlocal total_tokens
        total_tokens += usage.total_tokens

    register_usage_tracker(_track)

    allowed = [recomendacion] if recomendacion else ["aplicar", "dudar"]
    written = 0
    flagged = 0
    errors = 0

    with get_session() as session:
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
            .join(Evaluation, Evaluation.offer_id == Offer.id)
            .where(Offer.user_id == user_row.id)
            .where(Offer.estado == OfferEstado.evaluada)
            .where(Evaluation.recomendacion.in_(allowed))
            .order_by(Offer.fecha_detectada.desc())
        )
        if limit is not None:
            q = q.limit(limit)

        offers = list(session.execute(q).scalars().all())

        if not offers:
            click.echo("No hay ofertas evaluadas listas para redactar.")
            return

        click.echo(f"Redactando borradores para {len(offers)} oferta(s) de '{username}'…")

        for offer in offers:
            company_row = session.execute(
                select(Company).where(Company.id == offer.company_id)
            ).scalar_one_or_none()
            if company_row is None:
                click.echo(f"  SKIP [{offer.id}] {offer.titulo[:50]} — empresa no encontrada")
                continue

            evaluation = _eval_from_row(offer.evaluation) if offer.evaluation else None
            if evaluation is None:
                click.echo(f"  SKIP [{offer.id}] {offer.titulo[:50]} — sin evaluación")
                continue

            try:
                draft = await agent.write(offer, company_row, evaluation, user_profile)
            except Exception as exc:
                errors += 1
                click.echo(f"  ERROR [{offer.id}] {offer.titulo[:50]}: {exc}", err=True)
                continue

            if draft.needs_manual_context:
                flagged += 1
                tag = "FLAGGED (needs_manual_context)"
            else:
                written += 1
                tag = "OK"

            if not dry_run:
                path = draft_persistence.save_draft(draft, offer, user_profile, session)
                click.echo(f"  [{offer.id}] {offer.titulo[:50]} → {tag} ({path.name})")
            else:
                click.echo(f"  [dry-run] [{offer.id}] {offer.titulo[:50]} → {tag}")

        if dry_run:
            session.rollback()

    click.echo("\n=== Resumen de redacción ===")
    click.echo(f"  Borradores escritos:  {written}")
    click.echo(f"  Necesitan contexto:   {flagged}")
    click.echo(f"  Errores:              {errors}")
    click.echo(f"  Tokens usados:        {total_tokens}")
    if dry_run:
        click.echo("  (dry-run — sin cambios en DB ni ficheros)")
    click.echo("============================\n")


@cli.command("write-drafts")
@click.option("--user", required=True, help="Username for whom to generate application drafts.")
@click.option("--limit", default=None, type=int, help="Process at most N offers.")
@click.option(
    "--dry-run",
    "write_dry_run",
    is_flag=True,
    default=False,
    help="Generate drafts without persisting to the DB or disk.",
)
@click.option(
    "--recomendacion",
    default=None,
    type=click.Choice(["aplicar", "dudar"], case_sensitive=False),
    help="Only draft offers with this recommendation (default: both aplicar and dudar).",
)
@click.pass_obj
def write_drafts(
    obj: AppContext,
    user: str,
    limit: int | None,
    write_dry_run: bool,
    recomendacion: str | None,
) -> None:
    """Run the application-writer agent for evaluated offers (recomendacion aplicar/dudar)."""
    asyncio.run(
        _run_write_drafts(
            obj,
            user,
            limit=limit,
            dry_run=write_dry_run or obj.dry_run,
            recomendacion=recomendacion.lower() if recomendacion else None,
        )
    )


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
