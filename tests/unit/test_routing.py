"""Unit tests for confidence routing + the gather_more loop."""

from __future__ import annotations

from typing import Any

import pytest

from src.graph.nodes import gather_more as gather_mod
from src.graph.nodes.gather_more import make_gather_more
from src.graph.nodes.route import (
    ROUTE_END,
    ROUTE_GATHER_MORE,
    ROUTE_HUMAN_REVIEW,
    route_on_confidence,
)
from src.models.company import CompanyDossier
from src.models.fit import FitAssessment, ParsedOffer
from src.models.search import SearchResult


def _fit(**overrides: Any) -> FitAssessment:
    data: dict[str, Any] = {
        "fit_level": "moderate",
        "recommendation": "maybe",
        "score": 55,
        "reasoning": "x",
        "red_flags": [],
        "missing_info": [],
        "tailoring": None,
    }
    data.update(overrides)
    return FitAssessment.model_validate(data)


def _dossier() -> CompanyDossier:
    return CompanyDossier.model_validate(
        {
            "sector": "data",
            "tamano": "pyme",
            "ubicacion_hq": "Madrid",
            "descripcion": "Co.",
            "stack_tecnologico": [],
            "cultura_notas": ["nota previa"],
            "red_flags_detectadas": [],
            "productos_o_servicios": [],
            "equipo_ai_detectado": False,
            "fuentes": [],
        }
    )


def _parsed() -> ParsedOffer:
    return ParsedOffer.model_validate(
        {
            "title": "Data Engineer",
            "detected_language": "es",
            "seniority": None,
            "company": "Acme",
            "sector": None,
            "location": "Madrid",
            "remote_policy": "remote",
            "required_skills": [],
            "preferred_skills": [],
            "salary_raw": None,
            "languages": [],
            "contract_type": None,
            "sponsorship_mention": None,
        }
    )


# --------------------------------------------------------------------------
# route_on_confidence (pure)
# --------------------------------------------------------------------------


def test_skip_routes_to_end() -> None:
    assert route_on_confidence({"fit": _fit(recommendation="skip")}) == ROUTE_END  # type: ignore[arg-type]


def test_missing_info_loop0_routes_to_gather_more() -> None:
    state: Any = {"fit": _fit(missing_info=["salario"])}
    assert route_on_confidence(state) == ROUTE_GATHER_MORE


def test_missing_info_loop1_routes_to_human_review() -> None:
    # Cap is 1 (Phase 10.6 Task 09): a single gather pass, then proceed.
    state: Any = {"fit": _fit(missing_info=["salario"]), "loop_count": 1}
    assert route_on_confidence(state) == ROUTE_HUMAN_REVIEW


def test_missing_info_loop2_routes_to_human_review() -> None:
    state: Any = {"fit": _fit(missing_info=["salario"]), "loop_count": 2}
    assert route_on_confidence(state) == ROUTE_HUMAN_REVIEW


def test_clean_confident_routes_to_human_review() -> None:
    state: Any = {"fit": _fit(missing_info=[])}
    assert route_on_confidence(state) == ROUTE_HUMAN_REVIEW


# --------------------------------------------------------------------------
# gather_more
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gather_more_increments_and_folds_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    """gather_more searches missing_info, folds snippets into notes, bumps loop_count."""

    async def _fake_search(query: str, n: int = 10) -> list[SearchResult]:
        return [SearchResult(title="t", url="https://e.com", snippet=f"snippet for {query}")]

    monkeypatch.setattr(gather_mod, "search_web", _fake_search)

    node = make_gather_more()
    state: Any = {
        "parsed": _parsed(),
        "dossier": _dossier(),
        "fit": _fit(missing_info=["salario", "stack"]),
        "loop_count": 0,
    }

    out = await node(state)

    assert out["loop_count"] == 1
    notes = out["dossier"].cultura_notas
    assert "nota previa" in notes
    assert any("salario" in nstr for nstr in notes)
    assert any("stack" in nstr for nstr in notes)


@pytest.mark.asyncio
async def test_loop_terminates_within_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated gather_more + route reaches human_review at the cap, never spins."""

    async def _fake_search(query: str, n: int = 10) -> list[SearchResult]:
        return []

    monkeypatch.setattr(gather_mod, "search_web", _fake_search)
    node = make_gather_more()

    state: Any = {
        "parsed": _parsed(),
        "dossier": _dossier(),
        "fit": _fit(missing_info=["salario"]),
        "loop_count": 0,
    }

    passes = 0
    while route_on_confidence(state) == ROUTE_GATHER_MORE:
        passes += 1
        assert passes <= 1  # cap is firm (1); cannot spin
        state.update(await node(state))

    assert route_on_confidence(state) == ROUTE_HUMAN_REVIEW
    assert passes == 1
