"""Command-line interface for the job-agent system."""

from __future__ import annotations

import click

from src.services.profiles import load_profile, upsert_user_row


@click.group()
def cli() -> None:
    """Job-agent CLI."""


@cli.group()
def profile() -> None:
    """Commands for managing user profiles."""


@profile.command("load")
@click.option("--user", required=True, help="Username matching config/users/<user>.yaml")
def profile_load(user: str) -> None:
    """Validate a user YAML and upsert the corresponding users table row."""
    p = load_profile(user)
    upsert_user_row(p)
    roles = ", ".join(p.target_roles[:3])
    click.echo(f"OK  {p.username} ({p.nombre}) — {len(p.experiences)} exp, roles: {roles}")


if __name__ == "__main__":
    cli()
