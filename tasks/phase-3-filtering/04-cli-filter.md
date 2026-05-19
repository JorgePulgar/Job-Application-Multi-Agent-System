# Phase 3 · Task 04 — CLI: filter

## Objective
Promote `filter --user <username>` from stub to real command.

## Acceptance criteria
- [x] `python -m src.cli filter --user jorge` selects all offers with `estado='new'` for that user and runs `OfferFilter` on each.
- [x] `--limit N` flag for testing.
- [x] `--dry-run` prints decisions without writing to DB.
- [x] Final summary: relevant count, discarded count, red-flag-short-circuit count, tokens used.

## Files to create / modify
- `src/cli.py` (replace `filter` stub)

## Dependencies
- Phase 3 / Tasks 01, 02, 03

## Estimated effort
**S**

## Testing notes
Integration test seeds a few `new` offers, mocks the LLM, runs the command, asserts DB updates.
