"""Parallel scraping orchestration, dedup, and DB insertion."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import cast

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agents.job_scraper.adzuna import AdzunaScraper
from src.agents.job_scraper.base import BaseScraper
from src.agents.job_scraper.jooble import JoobleScraper
from src.agents.job_scraper.wttj import WTTJScraper
from src.db.base import get_session
from src.db.models import User
from src.models.job_offer import JobOffer
from src.models.user_profile import UserProfile
from src.services.dedup import dedup_within_run, filter_existing

log = structlog.get_logger(__name__)

ALL_PLATFORMS: tuple[str, ...] = ("adzuna", "jooble", "wttj")

# Module-level dict — patchable in tests.
_SCRAPERS: dict[str, type[BaseScraper]] = {
    "adzuna": AdzunaScraper,
    "jooble": JoobleScraper,
    "wttj": WTTJScraper,
}


@dataclass
class ScrapeRunSummary:
    """Result of a complete scrape run.

    Attributes:
        per_platform: Raw offer count per platform name.
        dedup_dropped: Offers removed during within-run deduplication.
        existing_dropped: Offers already in the DB that were skipped.
        written: New offers written to the DB (0 if ``dry_run`` is True).
        errors: Mapping from platform name to error message for failed scrapers.
        dry_run: Whether the run skipped all DB writes.
    """

    per_platform: dict[str, int] = field(default_factory=dict)
    dedup_dropped: int = 0
    existing_dropped: int = 0
    written: int = 0
    errors: dict[str, str] = field(default_factory=dict)
    dry_run: bool = False


async def _run_one(platform: str, profile: UserProfile) -> tuple[str, list[JobOffer], str | None]:
    """Run a single scraper and return ``(platform, offers, error_or_None)``.

    Errors are caught and returned as a string rather than raised, so the
    caller can continue with other platforms.

    Args:
        platform: Key in ``_SCRAPERS`` identifying which scraper to use.
        profile: User profile passed to ``scraper.search``.

    Returns:
        Tuple of platform name, scraped offers (empty on failure), and an
        error message string or ``None`` on success.
    """
    klass = _SCRAPERS[platform]
    try:
        async with klass() as scraper:
            offers = await scraper.search(profile)
            return platform, offers, None
    except Exception as exc:
        log.warning("scraper_failed", platform=platform, error=str(exc))
        return platform, [], str(exc)


def _get_or_create_user(profile: UserProfile, session: Session) -> int:
    """Return the DB ``users.id`` for *profile*, inserting a row if absent.

    Args:
        profile: Source of ``username`` and ``nombre``.
        session: Active SQLAlchemy session (must be flushed before use).

    Returns:
        Integer primary key of the user row.
    """
    row = session.execute(
        select(User).where(User.username == profile.username)
    ).scalar_one_or_none()
    if row is None:
        row = User(username=profile.username, nombre=profile.nombre)
        session.add(row)
        session.flush()
    return int(row.id)


async def run_scrape(
    profile: UserProfile,
    platforms: tuple[str, ...] = ALL_PLATFORMS,
    dry_run: bool = False,
) -> ScrapeRunSummary:
    """Run scrapers in parallel, deduplicate, filter existing, and persist.

    Errors from individual scrapers are caught and logged; the run continues
    with any successfully-scraped platforms. At least one working scraper is
    sufficient for exit code 0 from the CLI.

    Args:
        profile: User profile supplying target roles and identity.
        platforms: Which platform keys to run (filtered against ``_SCRAPERS``).
        dry_run: When ``True``, skip all DB writes and return candidate count.

    Returns:
        :class:`ScrapeRunSummary` with per-platform counts and error details.
    """
    summary = ScrapeRunSummary(dry_run=dry_run)

    valid_platforms = [p for p in platforms if p in _SCRAPERS]
    if not valid_platforms:
        return summary

    coroutines = [_run_one(p, profile) for p in valid_platforms]
    results = cast(
        list[tuple[str, list[JobOffer], str | None]],
        await asyncio.gather(*coroutines),
    )

    all_offers: list[JobOffer] = []
    for platform, offers, error in results:
        summary.per_platform[platform] = len(offers)
        if error is not None:
            summary.errors[platform] = error
        all_offers.extend(offers)

    if not all_offers:
        return summary

    before_dedup = len(all_offers)
    all_offers = dedup_within_run(all_offers)
    summary.dedup_dropped = before_dedup - len(all_offers)

    if dry_run:
        summary.written = len(all_offers)
        return summary

    with get_session() as session:
        user_id = _get_or_create_user(profile, session)

        before_filter = len(all_offers)
        new_offers = filter_existing(all_offers, session, user_id)
        summary.existing_dropped = before_filter - len(new_offers)

        for offer in new_offers:
            session.add(offer.to_db_offer(user_id))
        summary.written = len(new_offers)

    return summary
