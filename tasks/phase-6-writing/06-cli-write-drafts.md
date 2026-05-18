# Phase 6 · Task 06 — CLI: write-drafts

## Objective
Real CLI promoting the stub.

## Acceptance criteria
- [ ] `python -m src.cli write-drafts --user jorge` selects offers with `estado='evaluated'` and `recomendacion ∈ {aplicar, dudar}` for that user, generates drafts.
- [ ] `--limit N`, `--dry-run` (don't persist).
- [ ] `--recomendacion aplicar` to filter only strong recommendations.
- [ ] Summary: drafts written, drafts flagged `needs_manual_context`, tokens used.

## Files to create / modify
- `src/cli.py` (replace stub)

## Dependencies
- Phase 6 / Tasks 01-05

## Estimated effort
**S**

## Testing notes
Integration test against mocked LLM with one offer that passes lint, one that fails twice (gets flagged).
