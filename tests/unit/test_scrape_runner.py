"""Integration-level tests for the scrape runner — all scrapers and the DB are mocked."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, ClassVar

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.services.scrape_runner as runner
from src.agents.job_scraper.base import BaseScraper
from src.cli import cli
from src.db.base import Base
from src.db.models import Offer
from src.models.job_offer import JobOffer
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.services.scrape_runner import ALL_PLATFORMS, run_scrape

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _offer(titulo: str, empresa: str, ubicacion: str = "Madrid") -> JobOffer:
    return JobOffer(titulo=titulo, empresa=empresa, ubicacion=ubicacion, plataforma="test")


def _make_scraper_class(
    platform_name: str,
    offers: list[JobOffer],
    fail: bool = False,
) -> type[BaseScraper]:
    """Return a concrete BaseScraper subclass that serves canned offers in tests."""
    _offers = offers
    _fail = fail

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
            if _fail:
                raise RuntimeError(f"{self.name} scraper failed")
            return list(_offers)

    return _Mock


@pytest.fixture()
def profile() -> UserProfile:
    return UserProfile(
        username="testuser",
        nombre="Test User",
        email="test@example.com",
        location="Madrid",
        target_roles=["ML Engineer"],
        location_preference=LocationPreference(modality=Modality.hybrid),
        cv_summary="Test summary.",
    )


@pytest.fixture()
def db_engine():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def patch_scrapers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace all three scrapers with mocks returning a couple of offers each."""
    monkeypatch.setattr(
        runner,
        "_SCRAPERS",
        {
            "adzuna": _make_scraper_class("adzuna", [_offer("ML Engineer", "Acme")]),
            "jooble": _make_scraper_class("jooble", [_offer("Data Engineer", "DataCorp")]),
        },
    )


@pytest.fixture()
def patch_get_session(db_engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace get_session in scrape_runner with one backed by an in-memory DB."""

    @contextmanager
    def _fake() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session
            session.commit()

    monkeypatch.setattr(runner, "get_session", _fake)


# ---------------------------------------------------------------------------
# run_scrape — core behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scrape_writes_offers_to_db(
    profile: UserProfile,
    patch_scrapers: None,
    patch_get_session: None,
    db_engine: Any,
) -> None:
    summary = await run_scrape(profile)

    assert summary.written == 2
    assert summary.dedup_dropped == 0
    assert summary.existing_dropped == 0
    assert not summary.errors

    with Session(db_engine) as session:
        rows = list(session.execute(select(Offer)).scalars().all())
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_run_scrape_dry_run_no_db_writes(
    profile: UserProfile,
    patch_scrapers: None,
    patch_get_session: None,
    db_engine: Any,
) -> None:
    summary = await run_scrape(profile, dry_run=True)

    assert summary.dry_run is True
    assert summary.written == 2  # candidates, not persisted

    with Session(db_engine) as session:
        rows = list(session.execute(select(Offer)).scalars().all())
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_run_scrape_one_scraper_fails(
    profile: UserProfile,
    patch_get_session: None,
    monkeypatch: pytest.MonkeyPatch,
    db_engine: Any,
) -> None:
    monkeypatch.setattr(
        runner,
        "_SCRAPERS",
        {
            "adzuna": _make_scraper_class("adzuna", [_offer("ML Engineer", "Acme")]),
            "jooble": _make_scraper_class("jooble", [], fail=True),
        },
    )

    summary = await run_scrape(profile)

    assert "jooble" in summary.errors
    assert summary.written == 1  # adzuna still written
    assert summary.per_platform["jooble"] == 0
    assert summary.per_platform["adzuna"] == 1


@pytest.mark.asyncio
async def test_run_scrape_dedup_across_platforms(
    profile: UserProfile,
    patch_get_session: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same offer from two platforms should be deduped to one written row."""
    shared = _offer("ML Engineer", "Acme")
    monkeypatch.setattr(
        runner,
        "_SCRAPERS",
        {
            "adzuna": _make_scraper_class("adzuna", [shared]),
            "jooble": _make_scraper_class("jooble", [shared]),  # exact duplicate hash
        },
    )

    summary = await run_scrape(profile)

    assert summary.dedup_dropped >= 1
    assert summary.written == 1


@pytest.mark.asyncio
async def test_run_scrape_platform_filter(
    profile: UserProfile,
    patch_get_session: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only platforms in the requested tuple should be called."""
    called: list[str] = []

    def _track(name: str, offers: list[JobOffer]) -> type[BaseScraper]:
        _offers = offers
        _called = called

        class _T(BaseScraper):
            max_concurrency: ClassVar[int] = 1

            async def __aenter__(self) -> _T:
                _called.append(name)
                return self

            async def __aexit__(self, *args: Any) -> None:
                pass

            async def search(self, profile: UserProfile) -> list[JobOffer]:
                return list(_offers)

        _T.name = name  # type: ignore[attr-defined]
        return _T

    monkeypatch.setattr(
        runner,
        "_SCRAPERS",
        {
            "adzuna": _track("adzuna", [_offer("ML Engineer", "Acme")]),
            "jooble": _track("jooble", []),
        },
    )

    summary = await run_scrape(profile, platforms=("adzuna",))

    assert called == ["adzuna"]
    assert "jooble" not in summary.per_platform


@pytest.mark.asyncio
async def test_run_scrape_filters_already_existing(
    profile: UserProfile,
    patch_get_session: None,
    monkeypatch: pytest.MonkeyPatch,
    db_engine: Any,
) -> None:
    """A second run should not re-insert offers already in the DB."""
    monkeypatch.setattr(
        runner,
        "_SCRAPERS",
        {
            "adzuna": _make_scraper_class("adzuna", [_offer("ML Engineer", "Acme")]),
            "jooble": _make_scraper_class("jooble", []),
        },
    )

    summary1 = await run_scrape(profile)
    assert summary1.written == 1

    summary2 = await run_scrape(profile)
    assert summary2.existing_dropped == 1
    assert summary2.written == 0


@pytest.mark.asyncio
async def test_run_scrape_empty_platforms_returns_empty_summary(
    profile: UserProfile,
) -> None:
    summary = await run_scrape(profile, platforms=())
    assert summary.written == 0
    assert not summary.per_platform


# ---------------------------------------------------------------------------
# CLI scrape command
# ---------------------------------------------------------------------------


def test_cli_scrape_help() -> None:
    result = CliRunner().invoke(cli, ["scrape", "--help"])
    assert result.exit_code == 0
    assert "--platforms" in result.output
    assert "--user" in result.output


def test_cli_scrape_invalid_platform() -> None:
    result = CliRunner().invoke(cli, ["scrape", "--user", "jorge", "--platforms", "invalid"])
    assert result.exit_code != 0


def test_cli_scrape_all_platforms_in_default() -> None:
    result = CliRunner().invoke(cli, ["scrape", "--help"])
    for platform in ALL_PLATFORMS:
        assert platform in result.output
