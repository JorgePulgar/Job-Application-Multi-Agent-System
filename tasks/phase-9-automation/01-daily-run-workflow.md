# Phase 9 · Task 01 — daily-run.yml workflow

## Objective
GitHub Actions workflow that runs the orchestrator every morning Madrid time.

## Acceptance criteria
- [x] `.github/workflows/daily-run.yml` with cron trigger at `05:00 UTC` (= **06:00 CET in winter, 07:00 CEST in summer** — favors summer alignment with "7 AM Madrid"). Add a YAML comment explaining the DST drift and that we deliberately don't add a second cron entry.
- [x] Manual `workflow_dispatch` also enabled.
- [x] Steps: checkout, set up Python 3.11, install `uv`, `uv sync`, `playwright install chromium`, `alembic upgrade head`, `python -m src.cli orchestrator run --all-users`.
- [x] All env vars from CLAUDE.md §5 mapped from GitHub repo secrets.
- [x] Final step: post Telegram summary (handled in Task 03; this task just wires it in).
- [x] `concurrency` block prevents overlapping runs.
- [x] Timeout: 45 minutes.

## Implementation notes
- Telegram summary is emitted by the orchestrator inside `run_for_all_users` (Task 03), so wiring = mapping `TELEGRAM_*` into the run step's env; no separate step.
- `workflow_dispatch` exposes a `dry_run` boolean (per testing notes) that injects the global `--dry-run` flag for safe first manual runs.
- `playwright install` uses `--with-deps chromium` for the Ubuntu runner.

## Files to create / modify
- `.github/workflows/daily-run.yml`

## Dependencies
- Phase 7 complete

## Estimated effort
**M**

## Testing notes
Trigger `workflow_dispatch` manually with a temporary "dry run only" toggle the first few times. Verify timing comment vs DST behavior.
