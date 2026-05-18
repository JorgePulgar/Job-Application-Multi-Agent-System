# Phase 2 · Task 03 — Adzuna scraper

## Objective
Implement the Adzuna scraper using the official REST API (no HTML scraping). Returns `JobOffer` objects.

## Acceptance criteria
- [ ] `src/agents/job_scraper/adzuna.py` implements `class AdzunaScraper(BaseScraper)`.
- [ ] Uses `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` from settings.
- [ ] For each target role in `profile.target_roles`, queries Spain (`country=es`) and returns deduplicated offers.
- [ ] Maps Adzuna response fields → `JobOffer` (`title`→`titulo`, `company.display_name`→`empresa`, `location.area[-1]`→`ubicacion`, `salary_min`/`salary_max`, `redirect_url`→`url`, `created`→`fecha_publicacion`).
- [ ] `modalidad` inferred from title/description keywords (`remoto`, `híbrido`, `presencial`); default `unknown`.
- [ ] Rate limit: max 25 req/min (Adzuna free tier is 250/day — be conservative).
- [ ] If the API key isn't set, raise a clear `MissingCredentialsError` instead of failing cryptically.

## Files to create / modify
- `src/agents/job_scraper/adzuna.py`
- `src/exceptions.py` (define `MissingCredentialsError`, `ScraperError`)
- `tests/unit/test_adzuna_scraper.py`

## Dependencies
- Phase 2 / Task 01
- Phase 2 / Task 02

## Estimated effort
**M**

## Testing notes
Use `respx` to mock Adzuna API responses (sample fixture committed under `tests/fixtures/adzuna_*.json`). Assert correct mapping and that missing credentials raise the expected error.
