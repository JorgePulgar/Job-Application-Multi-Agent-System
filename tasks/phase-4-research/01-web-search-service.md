# Phase 4 · Task 01 — Web search service (Bing v7 + DuckDuckGo fallback)

## Objective
A single `search_web(query, n=10)` interface backed by Bing if a key is configured, otherwise DuckDuckGo. Detect availability at runtime; never crash if Bing is absent.

## Acceptance criteria
- [x] `src/services/web_search.py` exposes `async def search_web(query: str, n: int = 10) -> list[SearchResult]` where `SearchResult` is `{title, url, snippet}` (Pydantic model).
- [x] Provider selection: if `BING_SEARCH_KEY` is set, use Bing; else use `duckduckgo-search`. The chosen provider is logged once on startup.
- [x] Polite rate limiting (max 5 req/s for Bing, 1 req/s for DDG).
- [x] Returns at most `n` results; trims and dedupes by URL.
- [x] No exceptions leak — failed search returns `[]` and logs a warning.

## Files to create / modify
- `src/services/web_search.py`
- `src/models/search.py`
- `tests/unit/test_web_search.py`

## Dependencies
- Phase 1 complete

## Estimated effort
**M**

## Testing notes
Mock both providers (`respx` for Bing, monkeypatch `duckduckgo_search.DDGS` for the fallback). Verify provider selection logic and the empty-on-failure behavior.
