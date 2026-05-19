"""Unit tests for BaseScraper and HTTP helpers."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import respx
import httpx

from src.agents.job_scraper.base import BaseScraper
from src.models.job_offer import JobOffer
from src.models.user_profile import UserProfile
from src.services.http import is_allowed, make_http_client


# ---------------------------------------------------------------------------
# Concrete stub for testing
# ---------------------------------------------------------------------------


class _StubScraper(BaseScraper):
    name = "stub"
    max_concurrency = 2

    async def search(self, profile: UserProfile) -> list[JobOffer]:
        return []


# ---------------------------------------------------------------------------
# BaseScraper — abstract enforcement
# ---------------------------------------------------------------------------


def test_base_scraper_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseScraper()  # type: ignore[abstract]


def test_concrete_scraper_can_be_instantiated() -> None:
    scraper = _StubScraper()
    assert scraper.name == "stub"


# ---------------------------------------------------------------------------
# BaseScraper — context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_opens_and_closes() -> None:
    async with _StubScraper() as scraper:
        assert scraper._client is not None
        assert scraper._semaphore is not None
    assert scraper._client is None


@pytest.mark.asyncio
async def test_client_raises_outside_context() -> None:
    scraper = _StubScraper()
    with pytest.raises(RuntimeError, match="context manager"):
        _ = scraper.client


@pytest.mark.asyncio
async def test_semaphore_raises_outside_context() -> None:
    scraper = _StubScraper()
    with pytest.raises(RuntimeError, match="context manager"):
        _ = scraper.semaphore


# ---------------------------------------------------------------------------
# BaseScraper — rate limiting (semaphore caps concurrency)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency() -> None:
    """Verify that at most max_concurrency tasks hold the semaphore at once."""
    max_concurrent = 0
    current = 0

    class _CountingScraper(BaseScraper):
        name = "counting"
        max_concurrency = 2

        async def search(self, profile: UserProfile) -> list[JobOffer]:
            return []

    async with _CountingScraper() as scraper:

        async def _task() -> None:
            nonlocal max_concurrent, current
            async with scraper.semaphore:
                current += 1
                max_concurrent = max(max_concurrent, current)
                await asyncio.sleep(0.01)
                current -= 1

        await asyncio.gather(*[_task() for _ in range(6)])

    assert max_concurrent <= 2


# ---------------------------------------------------------------------------
# make_http_client
# ---------------------------------------------------------------------------


def test_make_http_client_returns_async_client() -> None:
    client = make_http_client()
    assert isinstance(client, httpx.AsyncClient)


# ---------------------------------------------------------------------------
# is_allowed — robots.txt
# ---------------------------------------------------------------------------


def test_is_allowed_permits_when_robots_allows(tmp_path: Any) -> None:
    robots_txt = "User-agent: *\nAllow: /\n"
    with patch("src.services.http._fetch_robots") as mock_fetch:
        import urllib.robotparser
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(robots_txt.splitlines())
        mock_fetch.return_value = parser
        assert is_allowed("https://example.com/jobs/123") is True


def test_is_allowed_blocks_when_robots_disallows() -> None:
    robots_txt = "User-agent: *\nDisallow: /\n"
    with patch("src.services.http._fetch_robots") as mock_fetch:
        import urllib.robotparser
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(robots_txt.splitlines())
        mock_fetch.return_value = parser
        assert is_allowed("https://example.com/jobs/123") is False
