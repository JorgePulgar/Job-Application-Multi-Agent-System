"""Unit tests for the Phase 10.5 fit schemas (``src/models/fit.py``)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.db.models import Evaluation as DbEvaluation
from src.models.fit import (
    FitAssessment,
    ParsedOffer,
    RequirementMatch,
    SponsorshipSignal,
)


def _sample_fit(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "fit_level": "strong",
        "recommendation": "apply",
        "score": 82,
        "reasoning": "Stack y seniority encajan; sin blockers.",
        "red_flags": [],
        "missing_info": [],
        "tailoring": {
            "cv_emphasis": ["Azure OpenAI", "LangGraph"],
            "cover_letter_hook": "Su equipo de datos en expansión.",
            "gap_to_address": None,
        },
    }
    base.update(overrides)
    return base


def test_parsed_offer_round_trip() -> None:
    """ParsedOffer validates from a JSON-shaped dict and round-trips."""
    data: dict[str, object] = {
        "title": "ML Engineer",
        "detected_language": "en",
        "seniority": None,
        "company": "Acme AI",
        "sector": "fintech",
        "location": "Madrid",
        "remote_policy": "hybrid",
        "required_skills": ["python", "pytorch"],
        "preferred_skills": ["azure"],
        "salary_raw": None,
        "languages": ["english"],
        "contract_type": "permanent",
        "sponsorship_mention": None,
    }
    parsed = ParsedOffer.model_validate(data)
    assert parsed.detected_language == "en"
    assert parsed.model_dump() == data


def test_fit_assessment_round_trip() -> None:
    """FitAssessment validates from a dict including nested tailoring."""
    fit = FitAssessment.model_validate(_sample_fit())
    assert fit.tailoring is not None
    assert fit.tailoring.cv_emphasis == ["Azure OpenAI", "LangGraph"]


def test_score_upper_bound_rejected() -> None:
    """A score above 100 fails validation."""
    with pytest.raises(ValidationError):
        FitAssessment.model_validate(_sample_fit(score=101))


def test_score_lower_bound_rejected() -> None:
    """A negative score fails validation."""
    with pytest.raises(ValidationError):
        FitAssessment.model_validate(_sample_fit(score=-1))


@pytest.mark.parametrize(
    ("recommendation", "expected"),
    [("apply", "aplicar"), ("maybe", "dudar"), ("skip", "descartar")],
)
def test_to_evaluation_row_maps_recommendation(recommendation: str, expected: str) -> None:
    """to_evaluation_row produces a valid Evaluation with the Spanish recomendacion."""
    fit = FitAssessment.model_validate(
        _sample_fit(recommendation=recommendation, red_flags=["x"], missing_info=["y"])
    )
    row = fit.to_evaluation_row(offer_id=7)

    assert isinstance(row, DbEvaluation)
    assert row.offer_id == 7
    assert row.puntuacion == 82
    assert row.recomendacion == expected
    assert row.razonamiento == fit.reasoning
    assert row.contras == {"red_flags": ["x"], "missing_info": ["y"]}


def test_sponsorship_and_requirement_round_trip() -> None:
    """SponsorshipSignal and RequirementMatch validate from dicts."""
    sponsorship = SponsorshipSignal.model_validate(
        {
            "needs_sponsorship": None,
            "sponsorship_offered": True,
            "geo_viable_for_spain": True,
            "working_language": "english",
            "blocker": None,
        }
    )
    assert sponsorship.geo_viable_for_spain is True

    match = RequirementMatch.model_validate(
        {
            "items": [{"requirement": "5y Python", "status": "partial", "note": "3y"}],
            "standout_points": ["LLM agents"],
            "gaps": ["k8s"],
        }
    )
    assert match.items[0].status == "partial"
