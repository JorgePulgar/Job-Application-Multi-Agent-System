# Phase 1 · Task 06 — CLI skeleton

## Objective
A single `click` CLI with the command groups that subsequent phases will fill in. Each subcommand is a stub that prints "not implemented yet" but is wired up so the help tree is complete.

## Acceptance criteria
- [ ] `python -m src.cli --help` lists all v1 command groups:
  - `profile load --user <username>` (real, from Task 05)
  - `scrape --user <username>` (stub)
  - `filter --user <username>` (stub)
  - `research-companies --user <username>` (stub)
  - `evaluate --user <username>` (stub)
  - `write-drafts --user <username>` (stub)
  - `orchestrator run --user <username>` / `--all-users` (stub)
  - `db init`, `db migrate` (real wrappers around Alembic)
- [ ] CLI module structure: `src/cli.py` is the entry point, subcommands live in `src/cli/<group>.py` if useful, otherwise inline.
- [ ] Global options: `--log-level`, `--config-path`, `--dry-run`.
- [ ] Each stub prints `not implemented (phase N task M)` so future-Claude knows where to fill in.

## Files to create / modify
- `src/cli.py`
- `src/cli/` (if split)
- `tests/unit/test_cli_help.py`

## Dependencies
- Phase 1 / Task 05

## Estimated effort
**S**

## Testing notes
Test invokes `--help` and asserts all top-level commands are listed. Test each stub returns exit code 0 with the "not implemented" message.

## End of Phase 1
After this task: tell the user "Phase 1 complete. Verify: `uv sync && pre-commit run --all-files && pytest && python -m src.cli --help` all pass. Approve to start Phase 2."
