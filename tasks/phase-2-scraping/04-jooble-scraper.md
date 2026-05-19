# Phase 2 · Task 04 — Jooble scraper

## Objective
Implement the Jooble scraper using the official `POST /api/<key>` JSON endpoint.

## Acceptance criteria
- [x] `src/agents/job_scraper/jooble.py` implements `class JoobleScraper(BaseScraper)`.
- [x] Uses `JOOBLE_API_KEY` from settings.
- [x] For each target role × Spain, paginates until empty or 5 pages max.
- [x] Maps Jooble response → `JobOffer` (`title`, `company`, `location`, `snippet`→`descripcion`, `salary`, `link`→`url`, `updated`→`fecha_publicacion`).
- [x] Parses `salary` heuristically (free-text in Jooble) into `salario_min` / `salario_max` when possible — otherwise leaves both `None`.
- [x] Same `MissingCredentialsError` pattern as Adzuna.

## Files to create / modify
- `src/agents/job_scraper/jooble.py`
- `tests/unit/test_jooble_scraper.py`

## Dependencies
- Phase 2 / Task 01
- Phase 2 / Task 02

## Estimated effort
**M**

## Testing notes
Mock `httpx` POST with `respx`. Include fixtures with varied `salary` strings (`"30000-35000 EUR"`, `"€2.500/mes"`, `null`) to test the parser.
