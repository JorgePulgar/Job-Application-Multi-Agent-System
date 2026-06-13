"""Jooble job scraper using the official POST JSON API."""

from __future__ import annotations

import contextlib
import datetime
import re
import unicodedata
from typing import Any

import structlog

from src.agents.job_scraper.base import BaseScraper
from src.exceptions import MissingCredentialsError, ScraperError
from src.models.job_offer import JobOffer, Modalidad
from src.models.user_profile import UserProfile
from src.services.experience_filter import matches, query_terms

log = structlog.get_logger(__name__)

_BASE_URL = "https://jooble.org/api"
_MAX_PAGES = 5

# Salary parsing patterns (salary field is free text in Jooble).
_RANGE_RE = re.compile(r"(\d[\d.,]*)[\s]*[-][\s]*(\d[\d.,]*)")
_SINGLE_RE = re.compile(r"(\d[\d.,]{2,})")  # at least 3 digits total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_number(raw: str) -> int:
    """Parse a European-formatted number string to int (strips . and , separators)."""
    return int(re.sub(r"[.,]", "", raw))


def _parse_salary(salary_raw: str | None) -> tuple[int | None, int | None]:
    """Heuristically extract (salary_min, salary_max) from a free-text salary string.

    Handles these common Jooble formats::

        "30000-35000 EUR"    → (30000, 35000)
        "30.000-35.000 EUR"  → (30000, 35000)
        "2.500€/mes"         → (30000, None)   # *12 for monthly
        "35000€/año"         → (35000, None)
        None / ""            → (None, None)

    Args:
        salary_raw: Free-text salary string from the Jooble API, or ``None``.

    Returns:
        Tuple of ``(salario_min, salario_max)`` as annual EUR integers, or
        ``(None, None)`` when parsing fails.
    """
    if not salary_raw:
        return None, None

    is_monthly = bool(re.search(r"/?\s*mes\b", salary_raw, re.IGNORECASE))

    range_match = _RANGE_RE.search(salary_raw)
    if range_match:
        lo = _strip_number(range_match.group(1))
        hi = _strip_number(range_match.group(2))
        if is_monthly:
            return lo * 12, hi * 12
        return lo, hi

    single_match = _SINGLE_RE.search(salary_raw)
    if single_match:
        val = _strip_number(single_match.group(1))
        if is_monthly:
            val *= 12
        return val, None

    return None, None


def _ascii_lower(text: str) -> str:
    """Lowercase and strip accents for accent-insensitive keyword matching."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def _infer_modalidad(title: str, snippet: str) -> Modalidad:
    """Infer work modality from keywords in title and job snippet."""
    text = _ascii_lower(title + " " + snippet)
    if any(kw in text for kw in ("remoto", "remote", "teletrabajo", "full remote")):
        return Modalidad.remote
    if any(kw in text for kw in ("hibrid", "hybrid")):
        return Modalidad.hybrid
    if any(kw in text for kw in ("presencial", "on-site", "onsite", "in-office")):
        return Modalidad.onsite
    return Modalidad.unknown


def _parse_result(raw: dict[str, Any]) -> JobOffer:
    """Map a single Jooble API job dict to a ``JobOffer``."""
    title: str = raw.get("title", "")
    snippet: str = raw.get("snippet", "")

    updated_raw: str = raw.get("updated", "")
    fecha: datetime.date | None = None
    if updated_raw:
        with contextlib.suppress(ValueError):
            fecha = datetime.date.fromisoformat(updated_raw[:10])

    sal_min, sal_max = _parse_salary(raw.get("salary"))

    return JobOffer(
        titulo=title,
        empresa=raw.get("company", ""),
        ubicacion=raw.get("location", ""),
        modalidad=_infer_modalidad(title, snippet),
        salario_min=sal_min,
        salario_max=sal_max,
        descripcion=snippet,
        url=raw.get("link", ""),
        plataforma="jooble",
        fecha_publicacion=fecha,
    )


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class JoobleScraper(BaseScraper):
    """Scraper for the Jooble job platform (Spain, POST JSON API).

    Args:
        api_key: Jooble API key. Falls back to ``JOOBLE_API_KEY`` env var.
    """

    name = "jooble"
    max_concurrency = 2

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        self._api_key = api_key

    async def __aenter__(self) -> JoobleScraper:
        await super().__aenter__()
        if not self._api_key:
            try:
                from src.config import get_settings

                self._api_key = get_settings().jooble_api_key
            except Exception:
                pass

        if not self._api_key:
            raise MissingCredentialsError(
                "JOOBLE_API_KEY must be set in .env. "
                "Register at https://jooble.org/api/about to obtain it."
            )
        return self

    async def _fetch_page(
        self, role: str, page: int, extra_keywords: str | None = None
    ) -> list[dict[str, Any]]:
        """POST one page of Jooble results for *role*.

        Jooble's public API has no seniority/experience parameter, so experience
        biasing is done by appending keywords to the free-text ``keywords`` field;
        the real guarantee is the post-fetch filter in :meth:`search`.

        Args:
            role: Job title / keyword to search for.
            page: 1-based page number.
            extra_keywords: Optional seniority keywords appended to ``keywords``.

        Returns:
            List of raw job dicts from the API.

        Raises:
            ScraperError: On non-2xx API responses.
        """
        url = f"{_BASE_URL}/{self._api_key}"
        keywords = f"{role} {extra_keywords}".strip() if extra_keywords else role
        payload = {"keywords": keywords, "location": "Spain", "page": page}

        async with self.semaphore:
            log.debug("jooble fetch", role=role, page=page)
            response = await self.client.post(url, json=payload)

        if response.status_code != 200:
            raise ScraperError(
                f"Jooble API returned {response.status_code} for role '{role}' page {page}: "
                f"{response.text[:200]}"
            )

        data: dict[str, Any] = response.json()
        jobs: list[dict[str, Any]] = data.get("jobs", [])
        return jobs

    async def search(self, profile: UserProfile) -> list[JobOffer]:
        """Search Jooble Spain for all target roles in *profile*.

        Paginates up to ``_MAX_PAGES`` per role and deduplicates across roles.

        Args:
            profile: User profile providing target roles.

        Returns:
            Deduplicated list of ``JobOffer`` instances.
        """
        seen: set[str] = set()
        offers: list[JobOffer] = []

        level = profile.experience_level
        extra_keywords = " ".join(query_terms(level)) if level else None

        for role in profile.target_roles:
            for page in range(1, _MAX_PAGES + 1):
                try:
                    jobs = await self._fetch_page(role, page, extra_keywords=extra_keywords)
                except ScraperError:
                    log.warning("jooble fetch failed", role=role, page=page)
                    break

                if not jobs:
                    break

                for raw in jobs:
                    offer = _parse_result(raw)
                    if level and not matches(level, offer.titulo, offer.descripcion or ""):
                        continue
                    if offer.hash_unico not in seen:
                        seen.add(offer.hash_unico)
                        offers.append(offer)

        log.info("jooble search complete", total=len(offers), experience_level=level)
        return offers
