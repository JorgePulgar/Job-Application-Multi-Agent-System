"""Near-duplicate detection and DB-based deduplication for job offers."""

from __future__ import annotations

import structlog
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Offer
from src.models.job_offer import JobOffer

log = structlog.get_logger(__name__)


def dedup_within_run(offers: list[JobOffer], threshold: int = 92) -> list[JobOffer]:
    """Deduplicate a list of offers from a single scrape run.

    Two passes:

    1. Exact dedup — drops offers with a repeated ``hash_unico``.
    2. Near-dedup — drops offers whose ``titulo + empresa`` scores
       ``>= threshold`` (WRatio) against any already-kept offer.

    Args:
        offers: Raw scraped offers, possibly containing duplicates.
        threshold: WRatio score (0-100) above which two offers are considered
            near-duplicates. Default 92.

    Returns:
        Deduplicated list, preserving the first occurrence of each offer.
    """
    # Pass 1: exact hash dedup
    seen_hashes: set[str] = set()
    after_exact: list[JobOffer] = []
    for offer in offers:
        if offer.hash_unico not in seen_hashes:
            seen_hashes.add(offer.hash_unico)
            after_exact.append(offer)
    exact_dropped = len(offers) - len(after_exact)

    # Pass 2: rapidfuzz near-dedup on "titulo empresa"
    survivors: list[JobOffer] = []
    keys: list[str] = []
    for offer in after_exact:
        key = f"{offer.titulo} {offer.empresa}"
        if not any(fuzz.WRatio(key, k) >= threshold for k in keys):
            survivors.append(offer)
            keys.append(key)
    near_dropped = len(after_exact) - len(survivors)

    log.info(
        "dedup_within_run",
        exact_dropped=exact_dropped,
        near_dropped=near_dropped,
        survivors=len(survivors),
    )
    return survivors


def filter_existing(
    offers: list[JobOffer],
    session: Session,
    user_id: int,
) -> list[JobOffer]:
    """Drop offers already stored in the DB for *user_id*.

    Args:
        offers: Candidate offers to check.
        session: Active SQLAlchemy session.
        user_id: Database ``users.id`` used to scope the query.

    Returns:
        Offers not yet present in the database for this user.
    """
    if not offers:
        return offers

    candidate_hashes = {o.hash_unico for o in offers}
    existing: set[str] = set(
        session.execute(
            select(Offer.hash_unico).where(
                Offer.hash_unico.in_(candidate_hashes),
                Offer.user_id == user_id,
            )
        )
        .scalars()
        .all()
    )

    survivors = [o for o in offers if o.hash_unico not in existing]
    dropped = len(offers) - len(survivors)
    log.info("filter_existing", dropped=dropped, survivors=len(survivors))
    return survivors
