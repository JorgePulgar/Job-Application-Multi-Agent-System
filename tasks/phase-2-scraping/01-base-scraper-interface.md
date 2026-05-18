# Phase 2 · Task 01 — Base scraper interface

## Objective
Define the abstract interface every job scraper must implement, plus shared utilities (rate limiting, user-agent rotation, httpx client builder).

## Acceptance criteria
- [ ] `src/agents/job_scraper/base.py` declares `class BaseScraper(ABC)` with:
  - `name: str` (class attribute)
  - `async def search(self, profile: UserProfile) -> list[JobOffer]` (abstract)
  - `async def __aenter__` / `__aexit__` for managing httpx clients
- [ ] Built-in rate limiting via `asyncio.Semaphore` (configurable, default 2 concurrent requests).
- [ ] Shared `make_http_client()` factory in `src/services/http.py` returns a configured `httpx.AsyncClient` (timeout, retries via `httpx.HTTPTransport`, polite UA string).
- [ ] All scrapers respect `robots.txt` — helper `is_allowed(url: str, ua: str) -> bool` in `src/services/http.py`.
- [ ] No HTTP calls outside `src/services/http.py` or, for API-specific clients, inside scrapers that use the shared client factory.

## Files to create / modify
- `src/agents/job_scraper/__init__.py`
- `src/agents/job_scraper/base.py`
- `src/services/http.py`
- `tests/unit/test_scraper_base.py`

## Dependencies
- Phase 1 complete
- Phase 2 / Task 02 (JobOffer model) — start in parallel, finalize together

## Estimated effort
**M**

## Testing notes
Unit test confirms the abstract class can't be instantiated, rate limiter caps concurrency, and `robots.txt` checker returns expected results against a mocked response.
