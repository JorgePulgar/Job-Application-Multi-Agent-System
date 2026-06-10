"""Unit tests for the ``draft_cover_letter`` node."""

from __future__ import annotations

from typing import Any

import pytest

from src.graph.nodes import draft as draft_mod
from src.graph.nodes.draft import make_draft_cover_letter
from src.models.company import CompanyDossier
from src.models.fit import (
    CoverLetterDraft,
    FitAssessment,
    ParsedOffer,
    TailoringPointers,
)


class _FakeResult:
    def __init__(self, parsed: Any) -> None:
        self.parsed = parsed


class _SeqClient:
    """Returns a preset draft per call, in order."""

    def __init__(self, parsed_seq: list[Any]) -> None:
        self._seq = list(parsed_seq)
        self.calls = 0

    async def chat(self, **kwargs: Any) -> _FakeResult:
        self.calls += 1
        return _FakeResult(self._seq.pop(0))


class _FakeProfile:
    def cv_for_prompt(self) -> str:
        return "CV: Python, pipelines de datos."


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
            "required_skills": ["python"],
            "preferred_skills": [],
            "salary_raw": None,
            "languages": ["español"],
            "contract_type": None,
            "sponsorship_mention": None,
        }
    )


def _dossier() -> CompanyDossier:
    return CompanyDossier.model_validate(
        {
            "sector": "data",
            "tamano": "pyme",
            "ubicacion_hq": "Madrid",
            "descripcion": "Plataforma de datos.",
            "stack_tecnologico": ["python"],
            "cultura_notas": [],
            "red_flags_detectadas": [],
            "productos_o_servicios": ["plataforma de datos"],
            "equipo_ai_detectado": True,
            "fuentes": [],
        }
    )


def _fit() -> FitAssessment:
    return FitAssessment(
        fit_level="strong",
        recommendation="apply",
        score=85,
        reasoning="Encaje fuerte.",
        red_flags=[],
        missing_info=[],
        tailoring=TailoringPointers(
            cv_emphasis=["pipelines en Python"],
            cover_letter_hook="vuestra plataforma de datos",
            gap_to_address=None,
        ),
    )


_CLEAN_BODY = (
    "Hola, escribo por la vacante en Acme. Vuestra plataforma de datos encaja con "
    "mi experiencia construyendo pipelines en Python, donde reduje un 30% el tiempo "
    "de proceso. Me gustaría aportar ese trabajo a vuestro equipo. Un saludo."
)


def _clean_draft() -> CoverLetterDraft:
    return CoverLetterDraft(
        subject="Candidatura Data Engineer en Acme",
        body=_CLEAN_BODY,
        lead_angle="vuestra plataforma de datos",
        hook="plataforma de datos",
    )


def _banned_draft() -> CoverLetterDraft:
    return CoverLetterDraft(
        subject="Candidatura en Acme",
        body=f"Soy un profesional apasionado. {_CLEAN_BODY}",
        lead_angle="x",
        hook="plataforma de datos",
    )


def _state() -> Any:
    return {
        "offer_id": 1,
        "username": "jorge",
        "parsed": _parsed(),
        "dossier": _dossier(),
        "fit": _fit(),
        "human_decision": None,
    }


@pytest.fixture(autouse=True)
def _patch_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_mod, "load_profile", lambda _u: _FakeProfile())


@pytest.mark.asyncio
async def test_clean_draft_passes_first_try() -> None:
    """A clean draft is returned and not flagged; body has no AI disclosure."""
    client = _SeqClient([_clean_draft()])
    node = make_draft_cover_letter(client)  # type: ignore[arg-type]

    out = await node(_state())

    assert client.calls == 1
    assert out["needs_manual_context"] is False
    assert out["draft"] is not None
    body_low = out["draft"].body.lower()
    assert "inteligencia artificial" not in body_low
    assert "escrito con" not in body_low


@pytest.mark.asyncio
async def test_banned_word_triggers_regen() -> None:
    """A banned word in the first draft triggers a regen; the clean retry wins."""
    client = _SeqClient([_banned_draft(), _clean_draft()])
    node = make_draft_cover_letter(client)  # type: ignore[arg-type]

    out = await node(_state())

    assert client.calls == 2
    assert out["needs_manual_context"] is False
    assert out["draft"] is not None


@pytest.mark.asyncio
async def test_two_failures_flag_needs_manual_context() -> None:
    """Three banned drafts (initial + 2 regens) exhaust the cap and flag the offer."""
    client = _SeqClient([_banned_draft(), _banned_draft(), _banned_draft()])
    node = make_draft_cover_letter(client)  # type: ignore[arg-type]

    out = await node(_state())

    assert client.calls == 3
    assert out["needs_manual_context"] is True
    assert out["draft"] is None
