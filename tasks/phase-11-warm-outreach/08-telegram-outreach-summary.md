# Phase 11 · Task 08 — Telegram outreach summary + signal alerts

## Objective
Extend Telegram notifications to cover outreach.

## Acceptance criteria
- [ ] Daily summary message gets a new section: `Outreach`: drafts generated today (per user), drafts pending review, total `needs_manual_context`, weekly cap used (`X/Y`).
- [ ] Separate alert message after `scan-signals` runs: list of targets with fresh signals (max 10 per message; if more, summarize as "+N más"). Each entry: target name + company + signal type + URL.
- [ ] Alert is sent only if at least one fresh signal was detected.
- [ ] `Orchestrator.scan_signals_for_all_users` triggers the alert step at the end.

## Files to create / modify
- `src/services/telegram.py` (extend with a `format_signal_alert` helper)
- `src/orchestrator.py` (extend)
- `tests/unit/test_telegram_outreach.py`

## Dependencies
- Phase 11 / Tasks 03, 04, 07
- Phase 9 / Task 03

## Estimated effort
**S**

## Testing notes
Verify message formatting and that signal alerts don't fire on zero-signal runs.

## End of Phase 11
After this task: tell the user "Phase 11 complete. v1.1 is live. Validate by running the weekly scanner workflow and a daily run. Tag `v1.1.0` once happy."
