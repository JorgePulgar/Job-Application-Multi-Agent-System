"""Unit tests for src/models/draft.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.draft import Draft

_BODY = (
    "Estimado equipo de Acme, me dirijo a vosotros tras leer que acabais de "
    "lanzar vuestra plataforma de datos en tiempo real. Mi experiencia en "
    "pipelines de datos encaja directamente con ese reto y me gustaria aportar."
)


def _sample(**overrides: object) -> Draft:
    data: dict[str, object] = {
        "email_subject": "Candidatura: Data Engineer en Acme",
        "email_body": _BODY,
        "carta_presentacion": "## Carta\n\nContenido.",
        "experiencias_destacadas": [
            "5 anios en pipelines de datos",
            "Lideré migración a Azure",
            "Mentoría de juniors",
        ],
        "needs_manual_context": False,
        "flagged_reasons": [],
    }
    data.update(overrides)
    return Draft.model_validate(data)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_draft() -> None:
    d = _sample()
    assert d.email_subject.startswith("Candidatura")
    assert d.needs_manual_context is False
    assert len(d.experiencias_destacadas) == 3


def test_carta_optional() -> None:
    d = _sample(carta_presentacion=None)
    assert d.carta_presentacion is None


# ---------------------------------------------------------------------------
# Subject constraints
# ---------------------------------------------------------------------------


def test_subject_max_120() -> None:
    d = _sample(email_subject="x" * 120)
    assert len(d.email_subject) == 120


def test_subject_over_120_raises() -> None:
    with pytest.raises(ValidationError):
        _sample(email_subject="x" * 121)


def test_empty_subject_raises_when_not_flagged() -> None:
    with pytest.raises(ValidationError, match="email_subject"):
        _sample(email_subject="")


def test_empty_subject_ok_when_flagged() -> None:
    d = _sample(
        email_subject="",
        email_body="",
        needs_manual_context=True,
        flagged_reasons=["no_specific_hook"],
    )
    assert d.email_subject == ""
    assert d.needs_manual_context is True


# ---------------------------------------------------------------------------
# Body min length
# ---------------------------------------------------------------------------


def test_short_body_raises_when_not_flagged() -> None:
    with pytest.raises(ValidationError, match="email_body"):
        _sample(email_body="Demasiado corto.")


def test_short_body_ok_when_flagged() -> None:
    d = _sample(email_body="corto", needs_manual_context=True)
    assert d.email_body == "corto"


# ---------------------------------------------------------------------------
# experiencias_destacadas length
# ---------------------------------------------------------------------------


def test_three_bullets_ok() -> None:
    assert len(_sample(experiencias_destacadas=["a", "b", "c"]).experiencias_destacadas) == 3


def test_five_bullets_ok() -> None:
    d = _sample(experiencias_destacadas=[f"e{i}" for i in range(5)])
    assert len(d.experiencias_destacadas) == 5


def test_two_bullets_raises() -> None:
    with pytest.raises(ValidationError):
        _sample(experiencias_destacadas=["a", "b"])


def test_six_bullets_raises() -> None:
    with pytest.raises(ValidationError):
        _sample(experiencias_destacadas=[f"e{i}" for i in range(6)])


# ---------------------------------------------------------------------------
# List stripping
# ---------------------------------------------------------------------------


def test_bullets_stripped() -> None:
    d = _sample(experiencias_destacadas=["  a  ", " b ", "c"])
    assert d.experiencias_destacadas == ["a", "b", "c"]


def test_flagged_reasons_stripped() -> None:
    d = _sample(needs_manual_context=True, flagged_reasons=["  word  ", "  "])
    assert d.flagged_reasons == ["word"]


# ---------------------------------------------------------------------------
# to_db_row
# ---------------------------------------------------------------------------


def test_to_db_row_fields() -> None:
    d = _sample()
    row = d.to_db_row(offer_id=42, user_id=7)
    assert row.offer_id == 42
    assert row.user_id == 7
    assert row.asunto == d.email_subject
    assert row.cuerpo_email == d.email_body
    assert row.carta_presentacion == d.carta_presentacion
    assert row.estado == "pendiente"


def test_to_db_row_type() -> None:
    from src.db.models import Draft as DbDraft

    row = _sample().to_db_row(offer_id=1, user_id=1)
    assert isinstance(row, DbDraft)


def test_to_db_row_flagged_estado() -> None:
    d = _sample(
        email_subject="",
        email_body="",
        needs_manual_context=True,
        flagged_reasons=["no_specific_hook"],
    )
    row = d.to_db_row(offer_id=1, user_id=1)
    assert row.estado == "needs_manual_context"
    assert row.asunto is None
    assert row.cuerpo_email is None
