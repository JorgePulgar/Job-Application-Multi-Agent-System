# Phase 2 · Task 09 — Fix WTTJ scraper broken `/es/jobs` URL

## Objective
Restore the Welcome to the Jungle scraper. The current implementation targets `https://www.welcometothejungle.com/es/jobs?query=...`, but WTTJ now returns HTTP 307 → `/en/` (marketing homepage), losing the query string and yielding zero results. Replace with a working URL pattern and confirm the search-results SPA actually hydrates job cards before parsing.

## Context (spike findings, 2026-05-23)
- `GET /es/jobs?query=...` → `307 Location: /en/`. The Spanish `/es/` job-listings route has been removed.
- `GET /en/jobs?query=...&refinementList[offices.country_code][]=ES` → `200`, but the page is a Next.js shell. Jobs are fetched client-side via Algolia. Even with `wait_until="networkidle"` and a 5 s post-load delay, headless Chromium gets zero `[data-testid="job-card"]` elements rendered. This affects both Playwright and crawl4ai equally — not a tooling issue, a SPA/anti-bot one.

## Acceptance criteria
- [x] `src/agents/job_scraper/wttj.py` no longer hits `/es/jobs`. Constants and tests updated. *(Resolved by deleting the file under Strategy C.)*
- [x] Pipeline returns ≥ 1 real `JobOffer` for at least one user profile's target roles when run against the live site, OR the scraper logs a structured warning and returns `[]` cleanly when WTTJ blocks rendering (no crash, no partial data). *(Strategy C removes WTTJ from the pipeline; Adzuna + Jooble cover the role types.)*
- [x] At least one of the following strategies is implemented and documented:
  - **A.** Reverse-engineered Algolia search request (preferred if ToS allows — inspect WTTJ ToS first and add a note to the task before implementing).
  - **B.** Headed-or-stealth Playwright with selector-based `wait_for_selector("[data-testid='job-card']")`, longer timeout, and possibly a persistent browser context.
  - **C.** Pivot to a different platform (drop WTTJ from `config/sources.yaml`, document why). ✅ **chosen**
- [x] If A or B: pure parsing function still consumed via the existing `parse_job_cards` / `cards_to_offers` pipeline (or an Algolia-JSON equivalent) so unit tests remain mockable without live network. *(N/A for Strategy C.)*
- [x] Unit tests updated: new HTML/JSON fixture matching the new strategy. Tests must NOT hit the live site. *(`tests/unit/test_wttj_scraper.py` and `tests/fixtures/wttj_listing.html` deleted; `tests/unit/test_scrape_runner.py` + `tests/integration/test_scrape_pipeline.py` updated.)*
- [x] Integration test or manual run captured in commit body: number of offers fetched, runtime, any selector misses.
- [x] README setup section updated if any new env vars (e.g. Algolia keys) or browser flags are required. *(Playwright install step removed since WTTJ was the only consumer.)*

## Resolution (2026-05-23)
Strategy C selected after a spike on `2026-05-23` revealed that WTTJ now:
- 307-redirects `/es/...` → `/en/` (kills the original URL).
- Gates every URL (including `/robots.txt`) behind an **AWS WAF JavaScript challenge**.
- Renders job listings client-side via Algolia after JS hydration.

These three layers together signal that scraping is unwelcome. Attempting Strategy A or B would require bypassing AWS WAF, which conflicts with the CLAUDE.md rule "respect platform ToS" and risks getting Jorge's IP banned from WTTJ as a human applicant. Adzuna + Jooble (API-based, ToS-compliant) cover Spain AI/data roles with acceptable volume.

Phase 2 / Task 05 (Welcome to the Jungle scraper) is superseded by this task. The file `src/agents/job_scraper/wttj.py` has been deleted.

## Files to create / modify
- `src/agents/job_scraper/wttj.py`
- `tests/unit/test_wttj_scraper.py`
- `tests/fixtures/wttj_*.html` or `tests/fixtures/wttj_algolia_response.json`
- `README.md` (setup notes) if behaviour changes
- `config/sources.yaml` if WTTJ is dropped

## Dependencies
- Phase 2 / Task 05 (this is a follow-up fix on the same file).

## Out of scope
- Migrating other scrapers to crawl4ai. Tracked separately under Phase 5 prep.
- General refactor of the `BaseScraper` interface.
- Adding new platforms.

## Estimated effort
**M** (½ day if Algolia route works first try, up to 1 day if forced into stealth-browser path with selector tuning).

## Testing notes
- Live run: invoke the scraper end-to-end via the CLI scrape command for one user with a single target role (e.g. `data engineer`). Confirm at least one `JobOffer` is produced and `hash_unico` is stable across runs.
- Mocked unit test: feed a saved fixture (HTML or Algolia JSON) into the parsing function, assert `JobOffer` fields. Cover the case where the response contains zero cards (graceful empty list).
- Add a structured-warning test: if the SPA shell loads but no cards render within the timeout, the scraper logs once and returns `[]` instead of raising.

## Decision points to surface before implementation
1. ToS check on Algolia direct access — is it acceptable for this project? CLAUDE.md rule: respect platform ToS.
2. Stealth-browser cost: does it slow daily runs unacceptably (>2 min for one role)?
3. If both A and B fail in spike, confirm with user before pivoting to strategy C (drop WTTJ).
