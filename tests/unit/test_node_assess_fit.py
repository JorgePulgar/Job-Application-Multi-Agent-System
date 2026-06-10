"""Unit tests for the ``assess_fit`` fan-in node."""

from __future__ import annotations

from typing import Any

import pytest

from src.graph.nodes.assess_fit import AssessFitError, make_assess_fit
from src.models.company import CompanyDossier
from src.models.fit import (
    FitAssessment,
    ParsedOffer,
    RequirementItem,
    RequirementMatch,
    SponsorshipSignal,
    TailoringPointers,
)


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


def _parsed(**overrides: Any) -> ParsedOffer:
    data: dict[str, Any] = {
        "title": "Data Engineer",
        "detected_language": "es",
        "seniority": None,
        "company": "Acme",
        "sector": None,
        "location": "Madrid",
        "remote_policy": "remote",
        "required_skills": ["python"],
        "preferred_skills": [],
        "salary_raw": None,
        "languages": ["español"],
        "contract_type": None,
        "sponsorship_mention": None,
    }
    data.update(overrides)
    return ParsedOffer.model_validate(data)


def _dossier() -> CompanyDossier:
    return CompanyDossier.model_validate(
        {
            "sector": "data",
            "tamano": "pyme",
            "ubicacion_hq": "Madrid",
            "descripcion": "Data company.",
            "stack_tecnologico": ["python"],
            "cultura_notas": [],
            "red_flags_detectadas": [],
            "productos_o_servicios": ["ETL"],
            "equipo_ai_detectado": True,
            "fuentes": [],
        }
    )


def _sponsorship(**overrides: Any) -> SponsorshipSignal:
    data: dict[str, Any] = {
        "needs_sponsorship": False,
        "sponsorship_offered": None,
        "geo_viable_for_spain": True,
        "working_language": "español",
        "blocker": None,
    }
    data.update(overrides)
    return SponsorshipSignal.model_validate(data)


def _requirements() -> RequirementMatch:
    return RequirementMatch(
        items=[RequirementItem(requirement="python", status="met", note="5y")],
        standout_points=["pipelines"],
        gaps=[],
    )


def _state(**overrides: Any) -> Any:
    base: dict[str, Any] = {
        "parsed": _parsed(),
        "dossier": _dossier(),
        "sponsorship": _sponsorship(),
        "requirements": _requirements(),
        "username": "jorge",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_uses_4o_with_fit_response_format() -> None:
    """Node calls gpt-4o with response_format=FitAssessment and branch data."""
    fit = FitAssessment(
        fit_level="strong",
        recommendation="apply",
        score=85,
        reasoning="Encaje fuerte.",
        red_flags=[],
        missing_info=[],
        tailoring=TailoringPointers(
            cv_emphasis=["python"], cover_letter_hook="x", gap_to_address=None
        ),
    )
    client = _FakeClient(fit)
    node = make_assess_fit(client)  # type: ignore[arg-type]

    out = await node(_state())

    assert out["fit"].recommendation == "apply"
    call = client.calls[0]
    assert call["deployment"] == "4o"
    assert call["response_format"] is FitAssessment
    assert "geo_viable_for_spain" in call["user"]


@pytest.mark.asyncio
async def test_missing_degree_only_not_skip() -> None:
    """A missing-degree-only case stays apply/maybe (soft gap, never skip alone)."""
    fit = FitAssessment(
        fit_level="moderate",
        recommendation="maybe",
        score=57,
        reasoning="Falta el grado pedido.",
        red_flags=["Piden grado universitario"],
        missing_info=[],
        tailoring=TailoringPointers(
            cv_emphasis=["experiencia equivalente"], cover_letter_hook="x", gap_to_address="grado"
        ),
    )
    node = make_assess_fit(_FakeClient(fit))  # type: ignore[arg-type]

    out = await node(_state())

    assert out["fit"].recommendation != "skip"


@pytest.mark.asyncio
async def test_sponsorship_blocked_is_skip_with_red_flag_and_no_tailoring() -> None:
    """Sponsorship-needed-not-offered → skip, with a red flag and tailoring None."""
    fit = FitAssessment(
        fit_level="weak",
        recommendation="skip",
        score=10,
        reasoning="Visado necesario y no ofrecido.",
        red_flags=["Sin patrocinio de visado"],
        missing_info=[],
        tailoring=None,
    )
    state = _state(
        sponsorship=_sponsorship(
            needs_sponsorship=True,
            sponsorship_offered=False,
            geo_viable_for_spain=False,
            blocker="Sin patrocinio",
        )
    )
    node = make_assess_fit(_FakeClient(fit))  # type: ignore[arg-type]

    out = await node(state)

    assert out["fit"].recommendation == "skip"
    assert out["fit"].red_flags
    assert out["fit"].tailoring is None


@pytest.mark.asyncio
async def test_invalid_assessment_raises() -> None:
    """An invalid LLM result raises AssessFitError."""
    node = make_assess_fit(_FakeClient(None))  # type: ignore[arg-type]
    with pytest.raises(AssessFitError):
        await node(_state())
