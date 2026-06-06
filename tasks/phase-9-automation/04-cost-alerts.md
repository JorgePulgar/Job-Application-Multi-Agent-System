# Phase 9 · Task 04 — Cost alert via Telegram

## Objective
If a daily run's estimated cost exceeds a threshold, send a second Telegram message clearly flagged as an alert.

## Acceptance criteria
- [x] Setting `DAILY_COST_ALERT_EUR` (default `1.00`) in `Settings`.
- [x] After the summary message, if any user's `coste_estimado_eur` or the global total exceeds the threshold, send a follow-up message titled `⚠️ ALERTA DE COSTE` with the offending breakdown.
- [x] Alert message includes a hint about cause (e.g. "muchos drafts regenerados — revisa lint failures").
- [x] Threshold respected per-run, not cumulative.

## Implementation notes
- `Settings.daily_cost_alert_eur` (env `DAILY_COST_ALERT_EUR`, default 1.00).
- `format_cost_alert(results, threshold)` returns the alert or `None`; fires when the global run total OR any single user exceeds the threshold (per-run, not cumulative). `run_for_all_users` sends it after the summary, via `_cost_alert_threshold()` which reads the setting with a safe fallback.
- Tests cover below/above-threshold (global + single-user) and that exactly one alert is sent above threshold, none below.

## Files to create / modify
- `src/orchestrator.py` (extend)
- `src/config.py` (add setting)
- `tests/unit/test_cost_alert.py`

## Dependencies
- Phase 9 / Task 03

## Estimated effort
**S**

## Testing notes
Unit test: a synthetic run with cost above threshold triggers exactly one alert message; below threshold triggers none.

## End of Phase 9
After this task: tell the user "Phase 9 complete. Run the workflow manually once and confirm the Telegram summary arrives. Approve to start Phase 10 (polish + docs)."
