# Phase 9 · Task 04 — Cost alert via Telegram

## Objective
If a daily run's estimated cost exceeds a threshold, send a second Telegram message clearly flagged as an alert.

## Acceptance criteria
- [ ] Setting `DAILY_COST_ALERT_EUR` (default `1.00`) in `Settings`.
- [ ] After the summary message, if any user's `coste_estimado_eur` or the global total exceeds the threshold, send a follow-up message titled `⚠️ ALERTA DE COSTE` with the offending breakdown.
- [ ] Alert message includes a hint about cause (e.g. "muchos drafts regenerados — revisa lint failures").
- [ ] Threshold respected per-run, not cumulative.

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
