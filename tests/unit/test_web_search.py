"""Unit tests for src/services/web_search.py."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

import src.services.web_search as wsm
from src.models.search import SearchResult
from src.services.web_search import _dedupe_by_url, search_web

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BING_URL = "https://api.bing.microsoft.com/v7.0/search"

_BING_RESPONSE: dict[str, Any] = {
    "webPages": {
        "value": [
            {"name": "Title A", "url": "https://a.example.com", "snippet": "Snippet A"},
            {"name": "Title B", "url": "https://b.example.com", "snippet": "Snippet B"},
            {"name": "Title C", "url": "https://c.example.com", "snippet": "Snippet C"},
        ]
    }
}

_DDG_RESPONSE: list[dict[str, Any]] = [
    {"title": "DDG A", "href": "https://ddg-a.example.com", "body": "Body A"},
    {"title": "DDG B", "href": "https://ddg-b.example.com", "body": "Body B"},
]


def _fake_settings(*, bing_key: str | None = None) -> MagicMock:
    s = MagicMock()
    s.bing_search_key = bing_key
    s.bing_search_endpoint = _BING_URL
    return s


@pytest.fixture(autouse=True)
def reset_provider() -> None:
    """Reset module-level provider state between tests."""
    wsm._active_provider = ""


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def test_resolve_provider_bing_when_key_set() -> None:
    with patch("src.services.web_search.get_settings", return_value=_fake_settings(bing_key="k")):
        assert wsm._resolve_provider() == "bing"


def test_resolve_provider_ddg_when_no_key() -> None:
    with patch("src.services.web_search.get_settings", return_value=_fake_settings()):
        assert wsm._resolve_provider() == "ddg"


def test_resolve_provider_logs_once(caplog: pytest.LogCaptureFixture) -> None:
    with patch("src.services.web_search.get_settings", return_value=_fake_settings(bing_key="k")):
        wsm._resolve_provider()
        wsm._resolve_provider()  # second call — same provider, should not re-log

    # _active_provider stays "bing" after first call; second call produces no new log
    assert wsm._active_provider == "bing"


# ---------------------------------------------------------------------------
# Bing search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_web_bing_returns_results() -> None:
    respx.get(_BING_URL).mock(return_value=httpx.Response(200, json=_BING_RESPONSE))

    with patch("src.services.web_search.get_settings", return_value=_fake_settings(bing_key="k")):
        results = await search_web("machine learning jobs spain", n=10)

    assert len(results) == 3
    assert all(isinstance(r, SearchResult) for r in results)
    assert results[0].title == "Title A"
    assert results[0].url == "https://a.example.com"
    assert results[0].snippet == "Snippet A"


@pytest.mark.asyncio
@respx.mock
async def test_search_web_bing_respects_n_limit() -> None:
    respx.get(_BING_URL).mock(return_value=httpx.Response(200, json=_BING_RESPONSE))

    with patch("src.services.web_search.get_settings", return_value=_fake_settings(bing_key="k")):
        results = await search_web("query", n=2)

    assert len(results) == 2


@pytest.mark.asyncio
@respx.mock
async def test_search_web_bing_empty_response() -> None:
    respx.get(_BING_URL).mock(return_value=httpx.Response(200, json={}))

    with patch("src.services.web_search.get_settings", return_value=_fake_settings(bing_key="k")):
        results = await search_web("query")

    assert results == []


# ---------------------------------------------------------------------------
# DuckDuckGo search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_web_ddg_returns_results() -> None:
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(return_value=_DDG_RESPONSE)

    with (
        patch("src.services.web_search.get_settings", return_value=_fake_settings()),
        patch("duckduckgo_search.DDGS", return_value=mock_ddgs),
    ):
        results = await search_web("ai jobs", n=10)

    assert len(results) == 2
    assert results[0].title == "DDG A"
    assert results[0].url == "https://ddg-a.example.com"
    assert results[0].snippet == "Body A"


@pytest.mark.asyncio
async def test_search_web_ddg_skips_items_without_url() -> None:
    response_with_empty: list[dict[str, Any]] = [
        {"title": "OK", "href": "https://ok.example.com", "body": "Body"},
        {"title": "No URL", "href": "", "body": "Should be skipped"},
    ]
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(return_value=response_with_empty)

    with (
        patch("src.services.web_search.get_settings", return_value=_fake_settings()),
        patch("duckduckgo_search.DDGS", return_value=mock_ddgs),
    ):
        results = await search_web("query")

    assert len(results) == 1
    assert results[0].url == "https://ok.example.com"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_dedupe_by_url_removes_duplicates() -> None:
    results = [
        SearchResult(title="A", url="https://dup.example.com", snippet="s1"),
        SearchResult(title="B", url="https://unique.example.com", snippet="s2"),
        SearchResult(title="C", url="https://dup.example.com", snippet="s3"),
    ]
    deduped = _dedupe_by_url(results)
    assert len(deduped) == 2
    assert deduped[0].title == "A"  # first-seen preserved
    assert deduped[1].url == "https://unique.example.com"


def test_dedupe_by_url_empty_list() -> None:
    assert _dedupe_by_url([]) == []


# ---------------------------------------------------------------------------
# Error handling — failed search returns empty list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_web_bing_http_error_returns_empty() -> None:
    respx.get(_BING_URL).mock(return_value=httpx.Response(500))

    with patch("src.services.web_search.get_settings", return_value=_fake_settings(bing_key="k")):
        results = await search_web("query")

    assert results == []


@pytest.mark.asyncio
async def test_search_web_ddg_exception_returns_empty() -> None:
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(side_effect=RuntimeError("DDG down"))

    with (
        patch("src.services.web_search.get_settings", return_value=_fake_settings()),
        patch("duckduckgo_search.DDGS", return_value=mock_ddgs),
    ):
        results = await search_web("query")

    assert results == []
