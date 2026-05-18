# Phase 11 · Task 07 — Signal scanner service + weekly-signals.yml

## Objective
Weekly job that re-checks saved targets for new public activity, populates `outreach_signals`, and flags fresh ones for priority drafting next day.

## Acceptance criteria
- [ ] `src/services/signal_scanner.py` exposes `async def scan_target(target: db.OutreachTarget) -> list[db.OutreachSignal]`.
- [ ] For each target with `estado ∉ {sent, replied, discarded}` and `fecha_ultimo_signal_check` older than 6 days:
  - Web searches: `"{nombre} {empresa}"`, `"{empresa}" news`, `"{nombre}" talk OR conferencia`, optionally `"{empresa}" funding OR ronda`.
  - Filter results to only those with dates within the last 14 days where parseable.
  - Classify each into a `tipo` (`new_post|company_news|role_change|talk_published|other`) via `gpt-4o-mini` structured output.
  - Insert non-duplicate `outreach_signals` rows.
- [ ] Update `target.fecha_ultimo_signal_check = now()`.
- [ ] CLI command `python -m src.cli orchestrator scan-signals --user <user>|--all-users`.
- [ ] `.github/workflows/weekly-signals.yml` cron Monday `06:00 UTC` (~08:00 CET; DST caveat as in daily-run).
- [ ] On fresh signals, the next daily run prioritizes those targets in the `WarmMessageWriter` queue (regenerate with new context derived from signals).

## Files to create / modify
- `src/services/signal_scanner.py`
- `src/cli.py` (add `orchestrator scan-signals`)
- `src/orchestrator.py` (priority-queue based on fresh signals)
- `.github/workflows/weekly-signals.yml`
- `tests/unit/test_signal_scanner.py`
- `tests/integration/test_signals_priority.py`

## Dependencies
- Phase 11 / Tasks 01-04

## Estimated effort
**L**

## Testing notes
Mock `search_web` + LLM classifier. Test dedup (same URL twice in different runs doesn't create two signal rows). Test priority ordering of WarmMessageWriter when fresh signals exist.
