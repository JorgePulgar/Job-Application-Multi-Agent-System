# Phase 7 · Task 03 — Run log persistence

## Objective
At the end of every orchestrator run, insert one `run_logs` row capturing what happened.

## Acceptance criteria
- [ ] `Orchestrator.run_for_user` writes a `run_logs` row with: `user_id`, `fecha_inicio`, `fecha_fin`, `ofertas_scrapeadas`, `ofertas_filtradas`, `drafts_generados`, `errores` (json: list of `{stage, offer_hash, error_class, message}`), `tokens_consumidos` (json: per-deployment input/cached/output counts), `coste_estimado_eur` (computed in Task 04).
- [ ] If the run is aborted by a fatal error, the row is still written with `fecha_fin = now()` and a top-level `errores` entry describing the abort.
- [ ] `RunResult` data class mirrors the row shape for in-memory use.

## Files to create / modify
- `src/orchestrator.py` (extend)
- `tests/integration/test_run_log.py`

## Dependencies
- Phase 7 / Tasks 01, 02

## Estimated effort
**S**

## Testing notes
Run pipeline, assert exactly one `run_logs` row inserted with the expected aggregate counts.
