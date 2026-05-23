# Phase 5 · Task 03 — CLI: evaluate

## Objective
Real CLI command running `ViabilityEvaluator` on each offer whose company has been researched.

## Acceptance criteria
- [x] `python -m src.cli evaluate --user jorge` selects offers with `estado='researching'` (or `relevant` if research was skipped) AND `empresa_id` not null, runs the evaluator.
- [x] `--limit N`, `--dry-run`.
- [x] Summary: per-recommendation counts, tokens used.

## Files to create / modify
- `src/cli.py` (replace `evaluate` stub)

## Dependencies
- Phase 5 / Task 02

## Estimated effort
**S**

## Testing notes
Integration test seeds 3 offers across 2 companies, mocks LLM with canned evaluations, asserts DB transitions.
