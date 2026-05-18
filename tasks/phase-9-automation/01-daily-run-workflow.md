# Phase 9 · Task 01 — daily-run.yml workflow

## Objective
GitHub Actions workflow that runs the orchestrator every morning Madrid time.

## Acceptance criteria
- [ ] `.github/workflows/daily-run.yml` with cron trigger at `05:00 UTC` (= **06:00 CET in winter, 07:00 CEST in summer** — favors summer alignment with "7 AM Madrid"). Add a YAML comment explaining the DST drift and that we deliberately don't add a second cron entry.
- [ ] Manual `workflow_dispatch` also enabled.
- [ ] Steps: checkout, set up Python 3.11, install `uv`, `uv sync`, `playwright install chromium`, `alembic upgrade head`, `python -m src.cli orchestrator run --all-users`.
- [ ] All env vars from CLAUDE.md §5 mapped from GitHub repo secrets.
- [ ] Final step: post Telegram summary (handled in Task 03; this task just wires it in).
- [ ] `concurrency` block prevents overlapping runs.
- [ ] Timeout: 45 minutes.

## Files to create / modify
- `.github/workflows/daily-run.yml`

## Dependencies
- Phase 7 complete

## Estimated effort
**M**

## Testing notes
Trigger `workflow_dispatch` manually with a temporary "dry run only" toggle the first few times. Verify timing comment vs DST behavior.
