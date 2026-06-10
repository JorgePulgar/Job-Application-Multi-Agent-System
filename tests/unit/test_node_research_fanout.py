"""Unit tests for the research fan-out nodes (company / sponsorship / match)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from src.graph.nodes import match_profile as match_mod
from src.graph.nodes import research_company as research_mod
from src.graph.nodes.match_profile import MatchProfileError, make_match_profile
from src.graph.nodes.research_company import make_research_company
from src.graph.nodes.sponsorship import SponsorshipError, make_extract_sponsorship
from src.models.company import CompanyDossier
from src.models.fit import ParsedOffer, RequirementMatch, SponsorshipSignal


class _FakeResult:
    def __init__(self, parsed: Any) -> None:
        self.parsed = parsed


class _FakeClient:
    def __init__(self, parsed: Any) -> None:
        self._parsed = parsed
        self.calls: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> _FakeResult:
        self.calls.append(kwargs)
        return _FakeResult(self._parsed)


@contextmanager
def _null_session() -> Iterator[object]:
    yield object()


def _parsed(**overrides: Any) -> ParsedOffer:
    data: dict[str, Any] = {
        "title": "ML Engineer",
        "detected_language": "en",
        "seniority": None,
        "company": "Acme AI",
        "sector": None,
        "location": "San Francisco, USA",
        "remote_policy": "onsite",
        "required_skills": ["python", "pytorch"],
        "preferred_skills": ["azure"],
        "salary_raw": None,
        "languages": ["english"],
        "contract_type": None,
        "sponsorship_mention": "No visa sponsorship available",
    }
    data.update(overrides)
    return ParsedOffer.model_validate(data)


def _dossier() -> CompanyDossier:
    return CompanyDossier.model_validate(
        {
            "sector": "ai",
            "tamano": "startup",
            "ubicacion_hq": "San Francisco",
            "descripcion": "AI startup.",
            "stack_tecnologico": ["python"],
            "cultura_notas": [],
            "red_flags_detectadas": [],
            "productos_o_servicios": ["LLM platform"],
            "equipo_ai_detectado": True,
            "fuentes": [],
        }
    )


# --------------------------------------------------------------------------
# research_company
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_company_reuses_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """The node delegates to CompanyResearcher and returns its dossier."""
    seen: dict[str, str] = {}

    class _FakeResearcher:
        def __init__(self, client: Any, session: Any) -> None:
            pass

        async def research(self, name: str) -> CompanyDossier:
            seen["name"] = name
            return _dossier()

    monkeypatch.setattr(research_mod, "CompanyResearcher", _FakeResearcher)
    node = make_research_company(_FakeClient(None), _null_session)  # type: ignore[arg-type]

    out = await node({"parsed": _parsed(), "username": "jorge"})

    assert isinstance(out["dossier"], CompanyDossier)
    assert seen["name"] == "Acme AI"


# --------------------------------------------------------------------------
# extract_sponsorship
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sponsorship_us_onsite_blocked() -> None:
    """A US-onsite no-sponsorship JD surfaces geo_viable=False + a blocker."""
    signal = SponsorshipSignal(
        needs_sponsorship=True,
        sponsorship_offered=False,
        geo_viable_for_spain=False,
        working_language="english",
        blocker="Onsite in the USA with no visa sponsorship.",
    )
    client = _FakeClient(signal)
    node = make_extract_sponsorship(client)  # type: ignore[arg-type]

    out = await node({"parsed": _parsed(), "username": "jorge"})

    assert out["sponsorship"].geo_viable_for_spain is False
    assert out["sponsorship"].blocker is not None
    assert client.calls[0]["deployment"] == "mini"
    assert client.calls[0]["response_format"] is SponsorshipSignal


@pytest.mark.asyncio
async def test_sponsorship_invalid_raises() -> None:
    """An invalid sponsorship result raises SponsorshipError."""
    node = make_extract_sponsorship(_FakeClient(None))  # type: ignore[arg-type]
    with pytest.raises(SponsorshipError):
        await node({"parsed": _parsed(), "username": "jorge"})


# --------------------------------------------------------------------------
# match_profile
# --------------------------------------------------------------------------


class _FakeProfile:
    def cv_for_prompt(self) -> str:
        return "CV_MARKER: python, pytorch, azure."


@pytest.mark.asyncio
async def test_match_profile_reads_yaml_not_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """match_profile loads the YAML profile and embeds its CV in the prompt."""
    loaded_for: dict[str, str] = {}

    def _fake_load_profile(username: str) -> Any:
        loaded_for["username"] = username
        return _FakeProfile()

    monkeypatch.setattr(match_mod, "load_profile", _fake_load_profile)

    match = RequirementMatch(
        items=[],
        standout_points=["LLM agents"],
        gaps=["k8s"],
    )
    client = _FakeClient(match)
    node = make_match_profile(client)  # type: ignore[arg-type]

    out = await node({"parsed": _parsed(), "username": "jorge"})

    assert loaded_for["username"] == "jorge"
    assert out["requirements"].gaps == ["k8s"]
    assert client.calls[0]["deployment"] == "4o"
    assert "CV_MARKER" in client.calls[0]["system"]


@pytest.mark.asyncio
async def test_match_profile_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid match result raises MatchProfileError."""
    monkeypatch.setattr(match_mod, "load_profile", lambda _u: _FakeProfile())
    node = make_match_profile(_FakeClient(None))  # type: ignore[arg-type]
    with pytest.raises(MatchProfileError):
        await node({"parsed": _parsed(), "username": "jorge"})


# --------------------------------------------------------------------------
# fan-out disjointness
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fanout_writes_three_disjoint_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """The three branches together produce dossier + sponsorship + requirements."""

    class _FakeResearcher:
        def __init__(self, client: Any, session: Any) -> None:
            pass

        async def research(self, name: str) -> CompanyDossier:
            return _dossier()

    monkeypatch.setattr(research_mod, "CompanyResearcher", _FakeResearcher)
    monkeypatch.setattr(match_mod, "load_profile", lambda _u: _FakeProfile())

    state: Any = {"parsed": _parsed(), "username": "jorge"}
    research = make_research_company(_FakeClient(None), _null_session)  # type: ignore[arg-type]
    sponsorship = make_extract_sponsorship(  # type: ignore[arg-type]
        _FakeClient(
            SponsorshipSignal(
                needs_sponsorship=None,
                sponsorship_offered=None,
                geo_viable_for_spain=True,
                working_language=None,
                blocker=None,
            )
        )
    )
    match = make_match_profile(  # type: ignore[arg-type]
        _FakeClient(RequirementMatch(items=[], standout_points=[], gaps=[]))
    )

    merged: dict[str, Any] = {}
    merged.update(await research(state))
    merged.update(await sponsorship(state))
    merged.update(await match(state))

    assert set(merged) == {"dossier", "sponsorship", "requirements"}
