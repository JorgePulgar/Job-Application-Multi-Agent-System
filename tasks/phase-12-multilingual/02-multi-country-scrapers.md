# Phase 12 · Task 02 — Multi-country / multi-locale scrapers

> **v2 scope.** Requires explicit user approval after v1 + v1.1.

## Objective
Parameterize each scraper by country/locale instead of the hardcoded Spain endpoints. Adzuna currently hardcodes `https://api.adzuna.com/v1/api/jobs/es/search`; this must become country-driven.

## Acceptance criteria
- [ ] `BaseScraper` interface accepts a `country` (alpha-2) and `language` per search, sourced from the user profile + `sources.yaml`.
- [ ] Adzuna scraper builds the URL with the configured country segment (`/jobs/{country}/search`) instead of literal `es`.
- [ ] Jooble + WTTJ scrapers accept their country/locale equivalents.
- [ ] One scrape run fans out over the user's `target_countries × search_languages`, deduping across countries via the existing hash + rapidfuzz.
- [ ] A platform that does not support a requested country is skipped with a logged warning, not a crash.
- [ ] Modality keyword inference recognizes both Spanish and English terms (already partly true for Adzuna — verify and extend).

## Files to create / modify
- `src/agents/job_scraper/base.py`
- `src/agents/job_scraper/adzuna.py`
- `src/agents/job_scraper/jooble.py`
- `src/agents/job_scraper/wttj.py` (if present)
- `tests/unit/test_adzuna_scraper.py`, `test_jooble_scraper.py`

## Dependencies
- Phase 12 / Task 01

## Estimated effort
**L**
