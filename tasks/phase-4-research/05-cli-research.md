# Phase 4 · Task 05 — CLI: research-companies

## Objective
Real CLI command running `CompanyResearcher` over the unique set of companies referenced by this user's `relevant` offers.

## Acceptance criteria
- [ ] `python -m src.cli research-companies --user jorge` queries distinct company names from `offers` where `estado='relevant'` and `empresa_id` is null, researches each, links offers to the resulting `companies` row.
- [ ] `--force-refresh` bypasses cache.
- [ ] `--limit N` for testing.
- [ ] Final summary: companies researched, cache hits, tokens used.

## Files to create / modify
- `src/cli.py` (replace `research-companies` stub)

## Dependencies
- Phase 4 / Tasks 01-04

## Estimated effort
**S**

## Testing notes
Integration test seeds offers across 3 companies (one already cached), runs the command, asserts only 2 LLM calls fired.
