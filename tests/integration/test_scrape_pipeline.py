"""End-to-end integration test for the scrape → dedup → DB-write pipeline.

All network calls are mocked; the database is an in-memory SQLite instance.
Run with: uv run pytest tests/integration/ -v
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, ClassVar

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import src.services.scrape_runner as runner
from src.agents.job_scraper.base import BaseScraper
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Offer
from src.models.job_offer import JobOffer
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.services.scrape_runner import run_scrape

# ---------------------------------------------------------------------------
# Fixtures — small, deterministic offer sets with intentional overlaps
# ---------------------------------------------------------------------------


def _o(titulo: str, empresa: str, ubicacion: str, plataforma: str) -> JobOffer:
    return JobOffer(titulo=titulo, empresa=empresa, ubicacion=ubicacion, plataforma=plataforma)


# Adzuna returns 3 offers
_ADZUNA_OFFERS = [
    _o("ML Engineer", "Acme Fintech SL", "Madrid", "adzuna"),
    _o("Data Engineer", "DataCorp Barcelona", "Barcelona", "adzuna"),
    _o("AI Researcher", "University Lab", "Bilbao", "adzuna"),
]

# Jooble returns 3 offers — two overlap with Adzuna (same titulo+empresa+ubicacion)
_JOOBLE_OFFERS = [
    _o("ML Engineer", "Acme Fintech SL", "Madrid", "jooble"),  # dup
    _o("Data Engineer", "DataCorp Barcelona", "Barcelona", "jooble"),  # dup
    _o("Backend Developer", "Startup XYZ", "Valencia", "jooble"),
]

# Unique offers across all platforms: ML Engineer, Data Engineer, AI Researcher,
# Backend Developer = 4 unique out of 6 raw
_TOTAL_RAW = len(_ADZUNA_OFFERS) + len(_JOOBLE_OFFERS)  # 6
_EXPECTED_UNIQUE = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scraper_class(platform_name: str, offers: list[JobOffer]) -> type[BaseScraper]:
    _offers = offers

    class _Mock(BaseScraper):
        name: ClassVar[str] = platform_name
        max_concurrency: ClassVar[int] = 1

        async def __aenter__(self) -> _Mock:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: Any,
        ) -> None:
            pass

        async def search(self, profile: UserProfile) -> list[JobOffer]:
            return list(_offers)

    return _Mock


@pytest.fixture()
def profile() -> UserProfile:
    return UserProfile(
        username="testuser",
        nombre="Test User",
        email="test@example.com",
        location="Madrid",
        target_roles=["ML Engineer", "Data Engineer"],
        location_preference=LocationPreference(modality=Modality.hybrid),
        cv_summary="Senior ML/data engineer with 5 years of experience.",
    )


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(autouse=True)
def patch_scrapers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner,
        "_SCRAPERS",
        {
            "adzuna": _make_scraper_class("adzuna", _ADZUNA_OFFERS),
            "jooble": _make_scraper_class("jooble", _JOOBLE_OFFERS),
        },
    )


@pytest.fixture(autouse=True)
def patch_get_session(db_engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _fake() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session
            session.commit()

    monkeypatch.setattr(runner, "get_session", _fake)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicates_collapsed_to_unique_rows(
    profile: UserProfile,
    db_engine: Any,
) -> None:
    """8 raw offers (3 cross-platform dups) → 5 unique rows in the DB."""
    summary = await run_scrape(profile)

    assert summary.dedup_dropped == _TOTAL_RAW - _EXPECTED_UNIQUE
    assert summary.written == _EXPECTED_UNIQUE
    assert summary.existing_dropped == 0
    assert not summary.errors

    with Session(db_engine) as session:
        row_count = session.execute(select(func.count()).select_from(Offer)).scalar_one()
    assert row_count == _EXPECTED_UNIQUE


@pytest.mark.asyncio
async def test_all_rows_have_estado_nueva(
    profile: UserProfile,
    db_engine: Any,
) -> None:
    """Every persisted offer must start in the 'nueva' state."""
    await run_scrape(profile)

    with Session(db_engine) as session:
        estados = list(session.execute(select(Offer.estado)).scalars().all())

    assert all(e == OfferEstado.nueva for e in estados)


@pytest.mark.asyncio
async def test_hash_unico_is_unique_in_db(
    profile: UserProfile,
    db_engine: Any,
) -> None:
    """No two DB rows should share the same hash_unico."""
    await run_scrape(profile)

    with Session(db_engine) as session:
        total = session.execute(select(func.count()).select_from(Offer)).scalar_one()
        distinct = session.execute(select(func.count(Offer.hash_unico.distinct()))).scalar_one()

    assert total == distinct == _EXPECTED_UNIQUE


@pytest.mark.asyncio
async def test_second_run_inserts_zero_new_rows(
    profile: UserProfile,
    db_engine: Any,
) -> None:
    """Running the same scrape twice must not create duplicate DB rows."""
    first = await run_scrape(profile)
    assert first.written == _EXPECTED_UNIQUE

    second = await run_scrape(profile)
    assert second.written == 0
    assert second.existing_dropped == _EXPECTED_UNIQUE

    with Session(db_engine) as session:
        row_count = session.execute(select(func.count()).select_from(Offer)).scalar_one()
    assert row_count == _EXPECTED_UNIQUE


@pytest.mark.asyncio
async def test_per_platform_counts_match_raw_input(
    profile: UserProfile,
) -> None:
    """Summary must report raw offer counts per platform before dedup."""
    summary = await run_scrape(profile)

    assert summary.per_platform["adzuna"] == len(_ADZUNA_OFFERS)
    assert summary.per_platform["jooble"] == len(_JOOBLE_OFFERS)
