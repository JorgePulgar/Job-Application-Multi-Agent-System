# Phase 11 · Task 04 — Orchestrator integration + daily/weekly caps

## Objective
Wire outreach into the daily orchestrator pipeline, after evaluation, with strict volume caps.

## Acceptance criteria
- [ ] After Phase 7's evaluation step, the orchestrator iterates companies whose best score ≥ `OUTREACH_MIN_SCORE` (setting, default 75) and `priority_for_outreach=True`.
- [ ] For each qualifying company without a current `outreach_targets` row, run `PersonFinder` to seed candidates.
- [ ] Then run `WarmMessageWriter` for candidates in `draft` state with non-stale signals or fresh manual context.
- [ ] **Hard cap: max 2 new outreach drafts per user per day.** Surplus candidates are queued for next day (stay in `draft` state without a `mensaje_borrador`).
- [ ] **Hard cap: max 10 outreach drafts per user per week** (lookback 7 days on `outreach_targets.fecha_encontrado` where state ≠ `discarded`). Setting `OUTREACH_WEEKLY_CAP` (default 10) — enforce, do not exceed.
- [ ] `run_logs` extended (no schema change needed; use existing `errores`/json fields plus new keys in the `tokens_consumidos` JSON for outreach token usage).
- [ ] CLI `orchestrator run` runs outreach by default; `--no-outreach` flag to skip.

## Files to create / modify
- `src/orchestrator.py` (extend)
- `src/config.py` (add settings)
- `tests/integration/test_orchestrator_outreach.py`

## Dependencies
- Phase 11 / Tasks 01-03

## Estimated effort
**L**

## Testing notes
Integration test: seed 5 qualifying companies. Assert only 2 drafts produced; remaining 3 stay in `draft` without `mensaje_borrador`. Run a second day, assert next 2 are generated and weekly cap is respected.
