# Phase 7 · Task 02 — Per-offer error handling

## Objective
A single bad offer cannot kill the run. Each per-offer step is wrapped in try/except; failures are logged and the offer's state moves to `error` with a short reason.

## Acceptance criteria
- [ ] Helper `run_per_offer(stage_name, offers, fn)` in `src/orchestrator.py` that runs `fn(offer)` for each, catching everything except `KeyboardInterrupt`/`SystemExit`.
- [ ] On exception: set `offer.estado = 'error'`, store the exception class + message (no stack trace, no PII) into a new `offers.error_note` column (add via Alembic migration).
- [ ] Pipeline-level fatal errors (LLM auth failure, DB down) DO halt the run — surfaced clearly, exit non-zero.
- [ ] Test: an offer that raises during filtering is moved to `error` and the rest continue.

## Files to create / modify
- `src/orchestrator.py` (extend Task 01)
- `alembic/versions/<hash>_add_offer_error_note.py`
- `src/db/models.py` (add column)
- `tests/integration/test_orchestrator_errors.py`

## Dependencies
- Phase 7 / Task 01

## Estimated effort
**M**

## Testing notes
Inject a failing scraper / filter / writer in turn and assert orchestrator survives, with the offending offer in `error` state and `error_note` populated.
