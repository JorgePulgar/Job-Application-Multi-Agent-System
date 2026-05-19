# Phase 2 · Task 08 — Scraping integration tests

## Objective
Wrap up Phase 2 with at least one end-to-end test that exercises the full scrape → dedup → DB-write path with all scrapers mocked.

## Acceptance criteria
- [x] `tests/integration/test_scrape_pipeline.py` mocks Adzuna, Jooble, and WTTJ to return overlapping fixture offers.
- [x] Asserts that after a scrape run: dups are collapsed, DB rows have `estado = 'new'`, `hash_unico` is unique.
- [x] A second run of the same fixtures inserts zero new rows.
- [x] Coverage check (informational, not gated): scraper modules >= 70%.

## Files to create / modify
- `tests/integration/test_scrape_pipeline.py`
- `tests/fixtures/` (offer JSON / HTML samples if not already there)

## Dependencies
- Phase 2 / Tasks 01-07

## Estimated effort
**S**

## Testing notes
Verify in CI mode (no network) that this test passes. Keep fixtures small (3-5 offers each platform).

## End of Phase 2
After this task: tell the user "Phase 2 complete. Verify: `python -m src.cli scrape --user jorge --dry-run` runs cleanly; tests pass. Approve to start Phase 3."
