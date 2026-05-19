"""Abstract base class for all job scraper agents."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from types import TracebackType
from typing import ClassVar

import httpx

from src.models.job_offer import JobOffer
from src.models.user_profile import UserProfile
from src.services.http import make_http_client

_DEFAULT_CONCURRENCY = 2


class BaseScraper(ABC):
    """Abstract interface every job scraper must implement.

    Scrapers are used as async context managers so the underlying
    ``httpx.AsyncClient`` is properly opened and closed::

        async with AdzunaScraper() as scraper:
            offers = await scraper.search(profile)

    Attributes:
        name: Human-readable platform identifier (e.g. ``"adzuna"``).
        max_concurrency: Maximum simultaneous in-flight requests.
    """

    name: ClassVar[str]
    max_concurrency: ClassVar[int] = _DEFAULT_CONCURRENCY

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> BaseScraper:
        """Open the HTTP client and initialise the rate-limiting semaphore."""
        self._client = make_http_client()
        await self._client.__aenter__()
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers for subclasses
    # ------------------------------------------------------------------

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the active HTTP client (only valid inside the context manager).

        Raises:
            RuntimeError: If accessed outside the async context manager.
        """
        if self._client is None:
            raise RuntimeError(
                f"{self.__class__.__name__} must be used as an async context manager."
            )
        return self._client

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Return the concurrency semaphore.

        Raises:
            RuntimeError: If accessed outside the async context manager.
        """
        if self._semaphore is None:
            raise RuntimeError(
                f"{self.__class__.__name__} must be used as an async context manager."
            )
        return self._semaphore

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def search(self, profile: UserProfile) -> list[JobOffer]:
        """Search for job offers matching *profile*.

        Args:
            profile: The user profile whose target roles / location / filters
                should be used to build the search query.

        Returns:
            A list of ``JobOffer`` instances found on this platform.
        """
