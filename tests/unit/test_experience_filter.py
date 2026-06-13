"""Unit tests for experience-level biasing + filtering and its scraper wiring."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from src.agents.job_scraper.adzuna import AdzunaScraper
from src.agents.job_scraper.jooble import JoobleScraper
from src.models.user_profile import ExperienceLevel, UserProfile
from src.services.experience_filter import matches, query_terms

# ---------------------------------------------------------------------------
# Helper: query_terms + matches
# ---------------------------------------------------------------------------


def test_query_terms_union_es_en() -> None:
    terms = query_terms(ExperienceLevel.junior)
    assert "junior" in terms
    assert "becario" in terms  # es
    assert "entry level" in terms  # en
    assert len(terms) == len(set(terms))  # de-duplicated


@pytest.mark.parametrize(
    "level, title, desc, expected",
    [
        # junior (max 2 yrs)
        (ExperienceLevel.junior, "Junior ML Engineer", "0-1 años", True),
        (ExperienceLevel.junior, "ML Engineer", "Requisito: 5+ años", False),
        (ExperienceLevel.junior, "ML Engineer", "minimum 4 years required", False),
        (ExperienceLevel.junior, "ML Engineer", "2 years experience", True),
        (ExperienceLevel.junior, "ML Engineer", "no stated requirement", True),
        # mid (max 5 yrs)
        (ExperienceLevel.mid, "Engineer", "3-5 years", True),
        (ExperienceLevel.mid, "Engineer", "8 years required", False),
        # senior: open-ended, never dropped on years
        (ExperienceLevel.senior, "Engineer", "10+ years", True),
    ],
)
def test_matches(level: ExperienceLevel, title: str, desc: str, expected: bool) -> None:
    assert matches(level, title, desc) is expected


# ---------------------------------------------------------------------------
# Adzuna wiring
# ---------------------------------------------------------------------------

_ADZUNA_RESULTS = {
    "count": 2,
    "results": [
        {
            "title": "Junior ML Engineer",
            "company": {"display_name": "JuniorCo"},
            "location": {"area": ["Madrid"]},
            "description": "Buscamos junior, 0-1 años de experiencia.",
            "redirect_url": "https://adzuna/u1",
            "created": "2026-05-01",
        },
        {
            "title": "ML Engineer",
            "company": {"display_name": "SeniorCo"},
            "location": {"area": ["Madrid"]},
            "description": "Requisito imprescindible: 5+ años de experiencia.",
            "redirect_url": "https://adzuna/u2",
            "created": "2026-05-02",
        },
    ],
}

_PROFILE = {
    "username": "jorge",
    "nombre": "Jorge",
    "email": "jorge@example.com",
    "location": "Madrid",
    "target_roles": ["ML Engineer"],
    "location_preference": {"modality": "hybrid", "cities": []},
    "cv_summary": "Resumen.",
}


def _profile(**overrides: object) -> UserProfile:
    return UserProfile.model_validate({**_PROFILE, **overrides})


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_junior_drops_stealth_senior() -> None:
    route = respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(
        return_value=httpx.Response(200, json=_ADZUNA_RESULTS)
    )
    async with AdzunaScraper(app_id="id", app_key="key") as scraper:
        offers = await scraper.search(_profile(experience_level="junior"))

    assert [o.empresa for o in offers] == ["JuniorCo"]  # 5+ años offer dropped
    assert "what_or" in str(route.calls.last.request.url)  # query biased


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_senior_keeps_all() -> None:
    respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(
        return_value=httpx.Response(200, json=_ADZUNA_RESULTS)
    )
    async with AdzunaScraper(app_id="id", app_key="key") as scraper:
        offers = await scraper.search(_profile(experience_level="senior"))
    assert len(offers) == 2


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_no_level_no_filter_no_bias() -> None:
    route = respx.get("https://api.adzuna.com/v1/api/jobs/es/search/1").mock(
        return_value=httpx.Response(200, json=_ADZUNA_RESULTS)
    )
    async with AdzunaScraper(app_id="id", app_key="key") as scraper:
        offers = await scraper.search(_profile())  # no experience_level
    assert len(offers) == 2
    assert "what_or" not in str(route.calls.last.request.url)


# ---------------------------------------------------------------------------
# Jooble wiring
# ---------------------------------------------------------------------------

_JOOBLE_JOBS = {
    "jobs": [
        {
            "title": "Junior Data Engineer",
            "company": "JuniorCo",
            "location": "Madrid",
            "snippet": "Puesto junior, sin experiencia previa.",
            "link": "https://jooble/u1",
            "updated": "2026-05-01",
            "salary": "",
        },
        {
            "title": "Data Engineer",
            "company": "SeniorCo",
            "location": "Madrid",
            "snippet": "Se requieren 6 años de experiencia.",
            "link": "https://jooble/u2",
            "updated": "2026-05-02",
            "salary": "",
        },
    ]
}


@pytest.mark.asyncio
@respx.mock
async def test_jooble_junior_drops_stealth_senior() -> None:
    calls = {"n": 0}

    def _handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        # First page returns jobs; subsequent pages empty so pagination stops.
        body = _JOOBLE_JOBS if calls["n"] == 1 else {"jobs": []}
        return httpx.Response(200, json=body)

    route = respx.post(url__startswith="https://jooble.org/api/").mock(side_effect=_handler)

    async with JoobleScraper(api_key="key") as scraper:
        offers = await scraper.search(_profile(experience_level="junior"))

    assert [o.empresa for o in offers] == ["JuniorCo"]  # 6 años offer dropped
    payload = json.loads(route.calls[0].request.content)
    assert "junior" in payload["keywords"]  # seniority keywords appended


@pytest.mark.asyncio
@respx.mock
async def test_jooble_no_level_no_filter() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        body = _JOOBLE_JOBS if payload["page"] == 1 else {"jobs": []}
        return httpx.Response(200, json=body)

    respx.post(url__startswith="https://jooble.org/api/").mock(side_effect=_handler)

    async with JoobleScraper(api_key="key") as scraper:
        offers = await scraper.search(_profile())
    assert len(offers) == 2
