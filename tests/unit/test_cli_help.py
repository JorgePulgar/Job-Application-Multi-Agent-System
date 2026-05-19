"""Tests for the CLI skeleton: help output and stub behaviour."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from src.cli import cli

runner = CliRunner()


# ---------------------------------------------------------------------------
# Root --help lists all top-level commands
# ---------------------------------------------------------------------------


def test_root_help_exits_zero() -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command",
    ["profile", "db", "scrape", "filter", "research-companies", "evaluate", "write-drafts", "orchestrator"],
)
def test_root_help_lists_command(command: str) -> None:
    result = runner.invoke(cli, ["--help"])
    assert command in result.output


# ---------------------------------------------------------------------------
# Each group / command has its own --help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args",
    [
        ["profile", "--help"],
        ["profile", "load", "--help"],
        ["db", "--help"],
        ["db", "init", "--help"],
        ["db", "migrate", "--help"],
        ["scrape", "--help"],
        ["filter", "--help"],
        ["research-companies", "--help"],
        ["evaluate", "--help"],
        ["write-drafts", "--help"],
        ["orchestrator", "--help"],
        ["orchestrator", "run", "--help"],
    ],
)
def test_subcommand_help_exits_zero(args: list[str]) -> None:
    result = runner.invoke(cli, args)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Global options are visible in root help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("option", ["--log-level", "--config-path", "--dry-run"])
def test_global_options_present(option: str) -> None:
    result = runner.invoke(cli, ["--help"])
    assert option in result.output


# ---------------------------------------------------------------------------
# Stubs print "not implemented" and exit 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args",
    [
        ["filter", "--user", "jorge"],
        ["research-companies", "--user", "jorge"],
        ["evaluate", "--user", "jorge"],
        ["write-drafts", "--user", "jorge"],
        ["orchestrator", "run", "--all-users"],
    ],
)
def test_stubs_exit_zero_with_not_implemented(args: list[str]) -> None:
    result = runner.invoke(cli, args)
    assert result.exit_code == 0
    assert "not implemented" in result.output


# ---------------------------------------------------------------------------
# orchestrator run requires --user or --all-users
# ---------------------------------------------------------------------------


def test_orchestrator_run_no_args_exits_nonzero() -> None:
    result = runner.invoke(cli, ["orchestrator", "run"])
    assert result.exit_code != 0
