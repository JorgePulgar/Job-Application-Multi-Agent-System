"""Command-line interface entry point for the job-agent system.

Run with:  python -m src.cli --help
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from alembic.config import Config as AlembicConfig

from alembic import command as alembic_command
from src.services.profiles import load_profile, upsert_user_row

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
# scrape (stub — Phase 2)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--user", required=True, help="Username to scrape offers for.")
@click.pass_obj
def scrape(obj: AppContext, user: str) -> None:
    """Scrape job offers from all configured platforms for a user."""
    click.echo("not implemented (phase 2)")


# ---------------------------------------------------------------------------
# filter (stub — Phase 3)
# ---------------------------------------------------------------------------


@cli.command("filter")
@click.option("--user", required=True, help="Username whose new offers to filter.")
@click.pass_obj
def filter_offers(obj: AppContext, user: str) -> None:
    """Run the offer-filter agent on unprocessed offers."""
    click.echo("not implemented (phase 3)")


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
