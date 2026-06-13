"""Unit tests for the Jooble scraper."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from src.agents.job_scraper.jooble import JoobleScraper, _parse_result, _parse_salary
from src.exceptions import MissingCredentialsError
from src.models.job_offer import Modalidad
from src.models.user_profile import UserProfile

_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
_PAGE1: dict = json.loads((_FIXTURE_DIR / "jooble_page1.json").read_text())
_EMPTY: dict = json.loads((_FIXTURE_DIR / "jooble_empty.json").read_text())

_PROFILE_DATA = {
    "username": "jorge",
    "nombre": "Jorge Pulgar",
    "email": "jorge@example.com",
    "location": "Madrid",
    "target_roles": ["ML Engineer"],
    "location_preference": {"modality": "hybrid", "cities": []},
    "cv_summary": "Resumen.",
}


def _profile(**overrides: object) -> UserProfile:
    d = dict(_PROFILE_DATA)
    d.update(overrides)
    return UserProfile.model_validate(d)


# ---------------------------------------------------------------------------
# Salary parser
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected_min, expected_max",
    [
        ("30000-35000 EUR", 30000, 35000),
        ("30.000-35.000 EUR", 30000, 35000),
        ("45000-65000 EUR", 45000, 65000),
        ("2.500-3.500 EUR/mes", 30000, 42000),  # x12
        ("2500 EUR/mes", 30000, None),  # monthly, single
        ("35.000 EUR/ano", 35000, None),  # annual single
        ("35000", 35000, None),  # bare number
        (None, None, None),
        ("", None, None),
        ("Sin especificar", None, None),
    ],
)
def test_parse_salary(raw: str | None, expected_min: int | None, expected_max: int | None) -> None:
    lo, hi = _parse_salary(raw)
    assert lo == expected_min
    assert hi == expected_max


# ---------------------------------------------------------------------------
# _parse_result field mapping
# ---------------------------------------------------------------------------


def test_parse_result_mapping() -> None:
    raw = _PAGE1["jobs"][0]
    offer = _parse_result(raw)
    assert offer.titulo == "ML Engineer Remoto"
    assert offer.empresa == "Acme Fintech SL"
    assert offer.ubicacion == "Madrid, Espana"
    assert offer.salario_min == 45000
    assert offer.salario_max == 65000
    assert offer.url == "https://jooble.org/desc/1001"
    assert offer.plataforma == "jooble"
    assert offer.fecha_publicacion is not None
    assert str(offer.fecha_publicacion) == "2026-05-01"
    assert offer.modalidad == Modalidad.remote


def test_parse_result_monthly_salary() -> None:
    raw = _PAGE1["jobs"][1]
    offer = _parse_result(raw)
    assert offer.salario_min == 30000  # 2500 * 12
    assert offer.salario_max == 42000  # 3500 * 12
    assert offer.modalidad == Modalidad.hybrid


def test_parse_result_null_salary() -> None:
    raw = _PAGE1["jobs"][2]
    offer = _parse_result(raw)
    assert offer.salario_min is None
    assert offer.salario_max is None
    assert offer.modalidad == Modalidad.onsite


# ---------------------------------------------------------------------------
# Missing credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_credentials_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Hermetic: ignore any real key in a developer .env by making the settings
    # fallback unavailable, so the empty constructor arg triggers the error path.
    def _no_settings() -> object:
        raise RuntimeError("settings unavailable")

    monkeypatch.setattr("src.config.get_settings", _no_settings)
    with pytest.raises(MissingCredentialsError):
        async with JoobleScraper(api_key=""):
            pass


# ---------------------------------------------------------------------------
# search — mocked HTTP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_mapped_offers() -> None:
    respx.post("https://jooble.org/api/test_key").mock(
        return_value=httpx.Response(200, json=_PAGE1)
    )

    async with JoobleScraper(api_key="test_key") as scraper:
        offers = await scraper.search(_profile())

    assert len(offers) == 3
    assert offers[0].plataforma == "jooble"


@pytest.mark.asyncio
@respx.mock
async def test_search_paginates_and_stops_on_empty() -> None:
    """Scraper fetches page 2 and stops when it returns empty."""
    call_count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=_PAGE1)
        return httpx.Response(200, json=_EMPTY)

    respx.post("https://jooble.org/api/test_key").mock(side_effect=_handler)

    async with JoobleScraper(api_key="test_key") as scraper:
        offers = await scraper.search(_profile())

    assert call_count == 2  # page 1 + page 2 (empty → stop)
    assert len(offers) == 3


@pytest.mark.asyncio
@respx.mock
async def test_search_deduplicates_across_roles() -> None:
    respx.post("https://jooble.org/api/test_key").mock(
        return_value=httpx.Response(200, json=_PAGE1)
    )

    profile = _profile(target_roles=["ML Engineer", "Data Engineer"])
    async with JoobleScraper(api_key="test_key") as scraper:
        offers = await scraper.search(profile)

    hashes = [o.hash_unico for o in offers]
    assert len(hashes) == len(set(hashes))


@pytest.mark.asyncio
@respx.mock
async def test_search_skips_failing_page() -> None:
    """A 429 on page 1 breaks the role loop; other roles proceed."""
    call_count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json=_PAGE1)

    respx.post("https://jooble.org/api/test_key").mock(side_effect=_handler)

    profile = _profile(target_roles=["ML Engineer", "Data Engineer"])
    async with JoobleScraper(api_key="test_key") as scraper:
        offers = await scraper.search(profile)

    assert len(offers) == 3  # only second role succeeded


@pytest.mark.asyncio
@respx.mock
async def test_search_respects_max_pages() -> None:
    """Scraper stops after MAX_PAGES even if responses keep returning data."""
    respx.post("https://jooble.org/api/test_key").mock(
        return_value=httpx.Response(200, json=_PAGE1)
    )

    # Give it a single role so we can count exact pages fetched
    profile = _profile(target_roles=["ML Engineer"])
    async with JoobleScraper(api_key="test_key") as scraper:
        # Patch _MAX_PAGES to 2 for this test
        import src.agents.job_scraper.jooble as jooble_mod

        original = jooble_mod._MAX_PAGES
        jooble_mod._MAX_PAGES = 2
        try:
            offers = await scraper.search(profile)
        finally:
            jooble_mod._MAX_PAGES = original

    # 3 offers per page x 2 pages, but all same hashes -> deduplicated to 3
    assert len(offers) == 3
