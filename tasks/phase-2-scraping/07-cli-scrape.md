# Phase 2 · Task 07 — CLI: scrape

## Objective
Promote the Phase 1 stub `scrape --user <username>` to a real command that runs all scrapers, dedups, and writes new offers to the DB with state `new`.

## Acceptance criteria
- [x] `python -m src.cli scrape --user jorge` loads the profile, runs Adzuna + Jooble + WTTJ in parallel (`asyncio.gather`), dedups within the run, filters existing, and inserts the remainder.
- [x] `--platforms adzuna,jooble` flag to restrict which scrapers run.
- [x] `--dry-run` prints the new offer count per platform without writing to the DB.
- [x] Errors from one scraper do NOT kill the others — log and continue. Final exit code is 0 if at least one scraper succeeded.
- [x] Run summary printed at the end: per-platform counts, dedup-dropped, written.

## Files to create / modify
- `src/cli.py` (replace `scrape` stub)
- `src/services/scrape_runner.py` (orchestration helper kept out of CLI module)

## Dependencies
- Phase 2 / Tasks 03, 04, 05, 06

## Estimated effort
**M**

## Testing notes
Integration-level test mocking all three scrapers to return fixed offers; assert DB rows created and summary output matches expectations.
