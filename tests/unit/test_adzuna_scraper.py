"""Unit tests for the Adzuna scraper using respx mocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
import httpx

from src.agents.job_scraper.adzuna import AdzunaScraper, _infer_modalidad, _parse_result
from src.exceptions import MissingCredentialsError, ScraperError
from src.models.job_offer import Modalidad
from src.models.user_profile import UserProfile

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "adzuna_sample.json"
_SAMPLE: dict = json.loads(_FIXTURE.read_text())

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
# _infer_modalidad
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title, desc, expected",
    [
        ("ML Engineer Remoto", "", Modalidad.remote),
        ("Data Engineer", "teletrabajo total", Modalidad.remote),
        ("Backend Developer", "puesto hibrido en Madrid", Modalidad.hybrid),
        ("DevOps Engineer", "posición presencial", Modalidad.onsite),
        ("Python Dev", "Buscamos desarrollador.", Modalidad.unknown),
    ],
)
def test_infer_modalidad(title: str, desc: str, expected: Modalidad) -> None:
    assert _infer_modalidad(title, desc) == expected


# ---------------------------------------------------------------------------
# _parse_result field mapping
# ---------------------------------------------------------------------------


def test_parse_result_full_mapping() -> None:
    raw = _SAMPLE["results"][0]
    offer = _parse_result(raw)
    assert offer.titulo == "ML Engineer (Remoto)"
    assert offer.empresa == "Acme Fintech SL"
    assert offer.ubicacion == "Madrid"
    assert offer.salario_min == 45000
    assert offer.salario_max == 65000
    assert offer.url == "https://www.adzuna.es/jobs/details/1001"
    assert offer.plataforma == "adzuna"
    assert offer.fecha_publicacion is not None
    assert str(offer.fecha_publicacion) == "2026-05-01"
    assert offer.modalidad == Modalidad.remote


def test_parse_result_null_salary() -> None:
    raw = _SAMPLE["results"][2]
    offer = _parse_result(raw)
    assert offer.salario_min is None
    assert offer.salario_max is None


def test_parse_result_hybrid_inferred() -> None:
    raw = _SAMPLE["results"][1]
    offer = _parse_result(raw)
    assert offer.modalidad == Modalidad.hybrid


def test_parse_result_location_last_area() -> None:
    raw = _SAMPLE["results"][1]
    offer = _parse_result(raw)
    assert offer.ubicacion == "Barcelona"


def test_parse_result_empty_location() -> None:
    raw = {**_SAMPLE["results"][0], "location": {"area": []}}
    offer = _parse_result(raw)
    assert offer.ubicacion == ""


# ---------------------------------------------------------------------------
# AdzunaScraper — missing credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_credentials_raises() -> None:
    with pytest.raises(MissingCredentialsError):
        async with AdzunaScraper(app_id="", app_key=""):
            pass


# ---------------------------------------------------------------------------
# AdzunaScraper — search with mocked HTTP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_mapped_offers() -> None:
    respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    profile = _profile()
    async with AdzunaScraper(app_id="test_id", app_key="test_key") as scraper:
        offers = await scraper.search(profile)

    assert len(offers) == 3
    assert offers[0].empresa == "Acme Fintech SL"
    assert offers[1].empresa == "DataCorp Barcelona"


@pytest.mark.asyncio
@respx.mock
async def test_search_deduplicates_across_roles() -> None:
    """Same offer returned for two role queries → appears only once."""
    respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    profile = _profile(target_roles=["ML Engineer", "Data Engineer"])
    async with AdzunaScraper(app_id="test_id", app_key="test_key") as scraper:
        offers = await scraper.search(profile)

    hashes = [o.hash_unico for o in offers]
    assert len(hashes) == len(set(hashes)), "Duplicate hashes found"


@pytest.mark.asyncio
@respx.mock
async def test_search_continues_on_scraper_error() -> None:
    """A failing role query is skipped; other roles still return results."""
    single_result = {"count": 1, "results": [_SAMPLE["results"][0]]}

    call_count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, text="Too Many Requests")
        return httpx.Response(200, json=single_result)

    respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(side_effect=_handler)

    profile = _profile(target_roles=["ML Engineer", "Data Engineer"])
    async with AdzunaScraper(app_id="test_id", app_key="test_key") as scraper:
        offers = await scraper.search(profile)

    assert len(offers) == 1  # only the second role succeeded


@pytest.mark.asyncio
@respx.mock
async def test_search_empty_results() -> None:
    respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(
        return_value=httpx.Response(200, json={"count": 0, "results": []})
    )
    profile = _profile()
    async with AdzunaScraper(app_id="test_id", app_key="test_key") as scraper:
        offers = await scraper.search(profile)
    assert offers == []
