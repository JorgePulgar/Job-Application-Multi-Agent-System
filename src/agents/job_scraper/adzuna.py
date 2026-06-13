"""Adzuna job scraper using the official REST API."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import time
import unicodedata
from typing import Any

import structlog

from src.agents.job_scraper.base import BaseScraper
from src.exceptions import MissingCredentialsError, ScraperError
from src.models.job_offer import JobOffer, Modalidad
from src.models.user_profile import UserProfile
from src.services.experience_filter import matches, query_terms

log = structlog.get_logger(__name__)

_BASE_URL = "https://api.adzuna.com/v1/api/jobs/es/search"
_RESULTS_PER_PAGE = 50
_MIN_REQUEST_INTERVAL = 2.5  # seconds → ≤ 24 req/min, well under 250/day


def _ascii_lower(text: str) -> str:
    """Lowercase and strip accents for accent-insensitive keyword matching."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def _infer_modalidad(title: str, description: str) -> Modalidad:
    """Infer work modality from keywords in title and description."""
    text = _ascii_lower(title + " " + description)
    if any(kw in text for kw in ("remoto", "remote", "teletrabajo", "full remote")):
        return Modalidad.remote
    if any(kw in text for kw in ("hibrid", "hybrid")):
        return Modalidad.hybrid
    if any(kw in text for kw in ("presencial", "on-site", "onsite", "in-office")):
        return Modalidad.onsite
    return Modalidad.unknown


def _parse_result(raw: dict[str, Any]) -> JobOffer:
    """Map a single Adzuna API result dict to a ``JobOffer``."""
    areas: list[str] = raw.get("location", {}).get("area", [])
    ubicacion = areas[-1] if areas else ""

    created_raw: str = raw.get("created", "")
    fecha: datetime.date | None = None
    if created_raw:
        with contextlib.suppress(ValueError):
            fecha = datetime.date.fromisoformat(created_raw[:10])

    title: str = raw.get("title", "")
    desc: str = raw.get("description", "")
    sal_min = raw.get("salary_min")
    sal_max = raw.get("salary_max")

    return JobOffer(
        titulo=title,
        empresa=raw.get("company", {}).get("display_name", ""),
        ubicacion=ubicacion,
        modalidad=_infer_modalidad(title, desc),
        salario_min=int(sal_min) if sal_min is not None else None,
        salario_max=int(sal_max) if sal_max is not None else None,
        descripcion=desc,
        url=raw.get("redirect_url", ""),
        plataforma="adzuna",
        fecha_publicacion=fecha,
    )


class AdzunaScraper(BaseScraper):
    """Scraper for the Adzuna job platform (Spain, REST API).

    Args:
        app_id: Adzuna application ID. Falls back to ``ADZUNA_APP_ID`` env var.
        app_key: Adzuna application key. Falls back to ``ADZUNA_APP_KEY`` env var.
    """

    name = "adzuna"
    max_concurrency = 1  # conservative — free tier 250 req/day

    def __init__(self, app_id: str | None = None, app_key: str | None = None) -> None:
        super().__init__()
        self._app_id = app_id
        self._app_key = app_key
        self._last_request_at: float = 0.0

    async def __aenter__(self) -> AdzunaScraper:
        await super().__aenter__()
        # Resolve credentials lazily so tests can pass them directly.
        if not self._app_id or not self._app_key:
            try:
                from src.config import get_settings

                settings = get_settings()
                self._app_id = self._app_id or settings.adzuna_app_id
                self._app_key = self._app_key or settings.adzuna_app_key
            except Exception:
                pass  # handled by the check below

        if not self._app_id or not self._app_key:
            raise MissingCredentialsError(
                "ADZUNA_APP_ID and ADZUNA_APP_KEY must be set in .env. "
                "Register at https://developer.adzuna.com/ to obtain them."
            )
        return self

    async def _rate_limit(self) -> None:
        """Sleep if necessary to respect the per-minute rate limit."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _MIN_REQUEST_INTERVAL:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

    async def _fetch_page(
        self, role: str, page: int, what_or: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch one page of Adzuna results for *role*.

        Args:
            role: Job title / keyword to search for.
            page: 1-based page number.
            what_or: Optional space-joined seniority keywords passed to Adzuna's
                documented ``what_or`` param (results match ``what`` AND any of
                these), biasing toward the user's experience level.

        Returns:
            List of raw result dicts from the API.

        Raises:
            ScraperError: On non-2xx API responses.
        """
        async with self.semaphore:
            await self._rate_limit()
            url = f"{_BASE_URL}/{page}"
            params: dict[str, str | int] = {
                "app_id": self._app_id or "",
                "app_key": self._app_key or "",
                "what": role,
                "results_per_page": _RESULTS_PER_PAGE,
                "content-type": "application/json",
            }
            if what_or:
                params["what_or"] = what_or
            log.debug("adzuna fetch", role=role, page=page, experience_biased=bool(what_or))
            response = await self.client.get(url, params=params)

        if response.status_code != 200:
            raise ScraperError(
                f"Adzuna API returned {response.status_code} for role '{role}': "
                f"{response.text[:200]}"
            )
        data: dict[str, Any] = response.json()
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    async def search(self, profile: UserProfile) -> list[JobOffer]:
        """Search Adzuna Spain for all target roles in *profile*.

        Deduplicates results across roles using ``hash_unico``.

        Args:
            profile: User profile providing target roles and filters.

        Returns:
            Deduplicated list of ``JobOffer`` instances.
        """
        seen: set[str] = set()
        offers: list[JobOffer] = []

        level = profile.experience_level
        what_or = " ".join(query_terms(level)) if level else None

        for role in profile.target_roles:
            try:
                results = await self._fetch_page(role, page=1, what_or=what_or)
            except ScraperError:
                log.warning("adzuna search failed for role", role=role)
                continue

            for raw in results:
                offer = _parse_result(raw)
                if level and not matches(level, offer.titulo, offer.descripcion or ""):
                    continue
                if offer.hash_unico not in seen:
                    seen.add(offer.hash_unico)
                    offers.append(offer)

        log.info("adzuna search complete", total=len(offers), experience_level=level)
        return offers
