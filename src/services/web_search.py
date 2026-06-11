"""Web search service: Bing Search v7 with DuckDuckGo fallback."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from src.config import get_settings
from src.models.search import SearchResult

logger = structlog.get_logger(__name__)

_BING_MIN_INTERVAL: float = 1 / 5  # 5 req/s
_DDG_MIN_INTERVAL: float = 1.0  # 1 req/s

_active_provider: str = ""


class _RateLimiter:
    """Async rate limiter enforcing a minimum interval between calls."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until the minimum interval since the last call has elapsed."""
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


_bing_limiter = _RateLimiter(_BING_MIN_INTERVAL)
_ddg_limiter = _RateLimiter(_DDG_MIN_INTERVAL)


def _resolve_provider() -> str:
    """Return the active provider, logging once when it first resolves or changes.

    Returns:
        ``"bing"`` when ``BING_SEARCH_KEY`` is configured, otherwise ``"ddg"``.
    """
    global _active_provider
    settings = get_settings()
    provider = "bing" if settings.bing_search_key else "ddg"
    if provider != _active_provider:
        _active_provider = provider
        logger.info("web_search_provider_selected", provider=provider)
    return provider


async def _search_bing(query: str, n: int) -> list[SearchResult]:
    """Execute a Bing Search v7 query.

    Args:
        query: Search query string.
        n: Maximum results requested.

    Returns:
        List of ``SearchResult`` objects extracted from the response.
    """
    settings = get_settings()
    await _bing_limiter.acquire()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            settings.bing_search_endpoint,
            headers={"Ocp-Apim-Subscription-Key": settings.bing_search_key or ""},
            params={"q": query, "count": min(n, 50), "mkt": "es-ES"},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

    results: list[SearchResult] = []
    for item in data.get("webPages", {}).get("value", []):
        url: str = item.get("url", "")
        if url:
            results.append(
                SearchResult(
                    title=item.get("name", ""),
                    url=url,
                    snippet=item.get("snippet", ""),
                )
            )
    return results


async def _search_ddg(query: str, n: int) -> list[SearchResult]:
    """Execute a DuckDuckGo text search in a thread pool.

    Args:
        query: Search query string.
        n: Maximum results requested.

    Returns:
        List of ``SearchResult`` objects extracted from the response.
    """
    await _ddg_limiter.acquire()
    loop = asyncio.get_running_loop()

    def _sync() -> list[dict[str, Any]]:
        from duckduckgo_search import DDGS  # local import to allow monkeypatching in tests

        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=n))

    items: list[dict[str, Any]] = await loop.run_in_executor(None, _sync)
    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("href", ""),
            snippet=item.get("body", ""),
        )
        for item in items
        if item.get("href")
    ]


def _dedupe_by_url(results: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicate URLs, preserving first-seen order.

    Args:
        results: Raw result list potentially containing duplicate URLs.

    Returns:
        Deduplicated list with original order preserved.
    """
    seen: set[str] = set()
    out: list[SearchResult] = []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            out.append(r)
    return out


async def search_web(query: str, n: int = 10) -> list[SearchResult]:
    """Search the web and return up to ``n`` deduplicated results.

    Uses Bing Search v7 when ``BING_SEARCH_KEY`` is set in the environment,
    falling back to DuckDuckGo otherwise. A Bing auth failure (HTTP 401/403 -- an
    invalid or expired key) also falls back to DuckDuckGo, so a bad key degrades
    rather than killing research. Any other failure logs a warning and returns an
    empty list rather than propagating the exception.

    Args:
        query: Search query string.
        n: Maximum number of results (default 10).

    Returns:
        Deduplicated list of ``SearchResult`` objects, at most ``n`` items.
    """
    try:
        provider = _resolve_provider()
        if provider == "bing":
            try:
                results = await _search_bing(query, n)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (401, 403):
                    raise
                logger.warning(
                    "web_search_bing_auth_failed_falling_back_ddg",
                    status=exc.response.status_code,
                    query=query,
                )
                results = await _search_ddg(query, n)
        else:
            results = await _search_ddg(query, n)
        return _dedupe_by_url(results)[:n]
    except Exception as exc:
        logger.warning("web_search_failed", query=query, error=str(exc))
        return []
