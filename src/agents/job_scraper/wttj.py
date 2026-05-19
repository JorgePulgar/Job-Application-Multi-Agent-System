"""Welcome to the Jungle scraper using Playwright async (headless Chromium)."""

from __future__ import annotations

import asyncio
import random
import unicodedata
from typing import Any

import structlog
from bs4 import BeautifulSoup

from src.agents.job_scraper.base import BaseScraper
from src.models.job_offer import JobOffer, Modalidad
from src.models.user_profile import UserProfile
from src.services.http import is_allowed

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.welcometothejungle.com"
_SEARCH_PATH = "/es/jobs"
_MAX_DETAIL_PAGES = 50
_DELAY_MIN = 2.0
_DELAY_MAX = 5.0
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# CSS selectors — change these when WTTJ updates their DOM.
_SEL_CARD = '[data-testid="job-card"]'
_SEL_TITLE = '[data-testid="job-title"]'
_SEL_COMPANY = '[data-testid="company-name"]'
_SEL_LOCATION = '[data-testid="job-location"]'
_SEL_TAGS = '[data-testid="job-tag"]'


# ---------------------------------------------------------------------------
# Pure parsing helpers (testable without Playwright)
# ---------------------------------------------------------------------------


def _ascii_lower(text: str) -> str:
    """Lowercase and strip accents for keyword matching."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def _infer_modalidad_from_tags(tags: list[str]) -> Modalidad:
    """Infer work modality from job card tag strings."""
    combined = _ascii_lower(" ".join(tags))
    if any(kw in combined for kw in ("remote", "remoto", "teletrabajo")):
        return Modalidad.remote
    if any(kw in combined for kw in ("hibrid", "hybrid")):
        return Modalidad.hybrid
    if any(kw in combined for kw in ("presencial", "on-site", "onsite")):
        return Modalidad.onsite
    return Modalidad.unknown


def parse_job_cards(html: str) -> list[dict[str, Any]]:
    """Parse WTTJ search-results HTML into a list of raw card dicts.

    This is a pure function — no network or browser involvement — so it can
    be unit-tested with a saved HTML fixture.

    Args:
        html: Raw HTML string from a WTTJ search-results page.

    Returns:
        List of dicts with keys ``titulo``, ``empresa``, ``ubicacion``,
        ``url``, ``tags``. Cards that are missing a title are skipped with a
        structured warning logged.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(_SEL_CARD)
    results: list[dict[str, Any]] = []

    for card in cards:
        title_el = card.select_one(_SEL_TITLE)
        if not title_el:
            log.warning("wttj selector miss: job title not found — card skipped")
            continue

        company_el = card.select_one(_SEL_COMPANY)
        location_el = card.select_one(_SEL_LOCATION)
        link_el = card.select_one("a[href]")
        tag_els = card.select(_SEL_TAGS)

        href = link_el["href"] if link_el else ""
        url = f"{_BASE_URL}{href}" if href and str(href).startswith("/") else str(href)

        results.append(
            {
                "titulo": title_el.get_text(strip=True),
                "empresa": company_el.get_text(strip=True) if company_el else "",
                "ubicacion": location_el.get_text(strip=True) if location_el else "",
                "url": url,
                "tags": [t.get_text(strip=True) for t in tag_els],
            }
        )

    return results


def cards_to_offers(cards: list[dict[str, Any]]) -> list[JobOffer]:
    """Convert raw card dicts from ``parse_job_cards`` to ``JobOffer`` instances.

    Args:
        cards: Output of :func:`parse_job_cards`.

    Returns:
        List of ``JobOffer`` instances.
    """
    offers: list[JobOffer] = []
    for card in cards:
        offers.append(
            JobOffer(
                titulo=card["titulo"],
                empresa=card["empresa"],
                ubicacion=card["ubicacion"],
                modalidad=_infer_modalidad_from_tags(card["tags"]),
                url=card["url"],
                plataforma="wttj",
            )
        )
    return offers


# ---------------------------------------------------------------------------
# Playwright scraper
# ---------------------------------------------------------------------------


class WTTJScraper(BaseScraper):
    """Scraper for Welcome to the Jungle Spain using headless Chromium (Playwright).

    Setup: run ``playwright install chromium`` once before using this scraper.
    """

    name = "wttj"
    max_concurrency = 3

    def __init__(self) -> None:
        super().__init__()
        self._playwright: Any = None
        self._browser: Any = None

    async def __aenter__(self) -> WTTJScraper:
        await super().__aenter__()
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def _new_page(self) -> Any:
        """Open a new browser page with the shared UA string."""
        context = await self._browser.new_context(user_agent=_UA)
        return await context.new_page()

    async def _human_delay(self) -> None:
        """Sleep a randomised 2-5 s to mimic human browsing pace."""
        await asyncio.sleep(random.uniform(_DELAY_MIN, _DELAY_MAX))

    async def _fetch_search_page(self, role: str) -> str:
        """Load the WTTJ search results page for *role* and return its HTML.

        Args:
            role: Job title / keyword to search for.

        Returns:
            Full HTML of the search-results page, or empty string on error.
        """
        search_url = f"{_BASE_URL}{_SEARCH_PATH}?query={role.replace(' ', '+')}&page=1"

        if not is_allowed(search_url):
            log.warning("wttj robots.txt disallows this URL — skipping", url=search_url)
            return ""

        async with self.semaphore:
            page = await self._new_page()
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
                await self._human_delay()
                return str(await page.content())
            except Exception as exc:
                log.warning("wttj page load failed", url=search_url, error=str(exc))
                return ""
            finally:
                await page.context.close()

    async def _fetch_detail(self, url: str, sem: asyncio.Semaphore) -> str:
        """Fetch a single WTTJ job detail page and return its HTML."""
        async with sem:
            page = await self._new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await self._human_delay()
                return str(await page.content())
            except Exception as exc:
                log.warning("wttj detail load failed", url=url, error=str(exc))
                return ""
            finally:
                await page.context.close()

    def _parse_description(self, html: str) -> str:
        """Extract job description text from a WTTJ detail page."""
        soup = BeautifulSoup(html, "html.parser")
        desc_el = soup.select_one('[data-testid="job-description"]') or soup.select_one(
            "section.job-description"
        )
        if desc_el:
            return desc_el.get_text(separator="\n", strip=True)
        return ""

    async def search(self, profile: UserProfile) -> list[JobOffer]:
        """Search WTTJ Spain for all target roles in *profile*.

        Fetches search-results pages, parses cards, then optionally enriches
        up to ``_MAX_DETAIL_PAGES`` offers with full descriptions.

        Args:
            profile: User profile providing target roles.

        Returns:
            Deduplicated list of ``JobOffer`` instances.
        """
        seen: set[str] = set()
        offers: list[JobOffer] = []
        detail_sem = asyncio.Semaphore(_MAX_DETAIL_PAGES)
        detail_count = 0

        for role in profile.target_roles:
            html = await self._fetch_search_page(role)
            if not html:
                continue

            cards = parse_job_cards(html)
            role_offers = cards_to_offers(cards)

            for offer in role_offers:
                if offer.hash_unico in seen:
                    continue
                seen.add(offer.hash_unico)

                # Enrich with full description up to the hard cap.
                if offer.url and detail_count < _MAX_DETAIL_PAGES:
                    detail_html = await self._fetch_detail(offer.url, detail_sem)
                    detail_count += 1
                    if detail_html:
                        desc = self._parse_description(detail_html)
                        if desc:
                            offer = offer.model_copy(update={"descripcion": desc})

                offers.append(offer)

        log.info("wttj search complete", total=len(offers))
        return offers
