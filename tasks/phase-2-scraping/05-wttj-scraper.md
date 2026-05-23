# Phase 2 · Task 05 — Welcome to the Jungle scraper (Playwright)

> **Superseded by [Task 09](./09-fix-wttj-url-redirect.md) on 2026-05-23.** WTTJ removed all `/es/` job-listing routes and put every URL behind an AWS WAF JavaScript challenge. The scraper was dropped under Strategy C; Adzuna + Jooble cover Spain AI/data roles instead.

## Objective
Scrape Welcome to the Jungle's Spain job board with Playwright async, respecting ToS and rate limits. No login required — we read public results pages only.

## Acceptance criteria
- [x] `src/agents/job_scraper/wttj.py` implements `class WTTJScraper(BaseScraper)` using Playwright async.
- [x] Headless Chromium, randomized but realistic UA, 2-5s human-like delay between page loads.
- [x] For each target role, performs a single search → parses listing cards → optionally fetches detail page for `descripcion`.
- [x] Max 3 concurrent pages, hard cap of 50 detail pages per run.
- [x] Respects `robots.txt` (use helper from Task 01); if disallowed, log and skip without raising.
- [x] Playwright install step documented in README setup section (`playwright install chromium`).
- [x] Gracefully handles selector changes — log a structured warning, return what was parsed, don't crash the whole pipeline.

## Files to create / modify
- `src/agents/job_scraper/wttj.py`
- `tests/unit/test_wttj_scraper.py` (mock with a saved HTML fixture; do NOT hit the live site in tests)

## Dependencies
- Phase 2 / Task 01
- Phase 2 / Task 02

## Estimated effort
**L**

## Testing notes
Unit test feeds a saved HTML fixture into the parser function (extracted as a pure function from the scraper) and asserts `JobOffer` objects come out correctly. No live network in tests.
