"""Unit tests for src/models/evaluation.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.evaluation import ViabilityEvaluation


def _sample(**overrides: object) -> ViabilityEvaluation:
    data: dict[str, object] = {
        "score": 75,
        "ventajas": ["Stack moderno", "Trabajo remoto"],
        "desventajas": ["Salario no especificado"],
        "red_flags_match": [],
        "recomendacion": "aplicar",
        "reasoning": "Encaja bien con el perfil técnico y el sector objetivo.",
    }
    data.update(overrides)
    return ViabilityEvaluation.model_validate(data)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_aplicar() -> None:
    ev = _sample()
    assert ev.score == 75
    assert ev.recomendacion == "aplicar"


def test_valid_dudar() -> None:
    ev = _sample(recomendacion="dudar")
    assert ev.recomendacion == "dudar"


def test_valid_descartar() -> None:
    ev = _sample(recomendacion="descartar", score=10)
    assert ev.recomendacion == "descartar"


def test_score_boundaries() -> None:
    assert _sample(score=0).score == 0
    assert _sample(score=100).score == 100


# ---------------------------------------------------------------------------
# Score validator
# ---------------------------------------------------------------------------


def test_score_below_zero_raises() -> None:
    with pytest.raises(ValidationError, match="score"):
        _sample(score=-1)


def test_score_above_100_raises() -> None:
    with pytest.raises(ValidationError, match="score"):
        _sample(score=101)


# ---------------------------------------------------------------------------
# Ventajas length constraints
# ---------------------------------------------------------------------------


def test_ventajas_min_one_required() -> None:
    with pytest.raises(ValidationError):
        _sample(ventajas=[])


def test_ventajas_max_six_allowed() -> None:
    ev = _sample(ventajas=[f"Pro {i}" for i in range(6)])
    assert len(ev.ventajas) == 6


def test_ventajas_seven_raises() -> None:
    with pytest.raises(ValidationError):
        _sample(ventajas=[f"Pro {i}" for i in range(7)])


# ---------------------------------------------------------------------------
# Desventajas length constraints
# ---------------------------------------------------------------------------


def test_desventajas_zero_allowed() -> None:
    ev = _sample(desventajas=[])
    assert ev.desventajas == []


def test_desventajas_max_six_allowed() -> None:
    ev = _sample(desventajas=[f"Con {i}" for i in range(6)])
    assert len(ev.desventajas) == 6


def test_desventajas_seven_raises() -> None:
    with pytest.raises(ValidationError):
        _sample(desventajas=[f"Con {i}" for i in range(7)])


# ---------------------------------------------------------------------------
# Cross-field validator: red_flags_match + recomendacion
# ---------------------------------------------------------------------------


def test_red_flags_with_descartar_ok() -> None:
    ev = _sample(red_flags_match=["sin_contrato_indefinido"], recomendacion="descartar")
    assert ev.recomendacion == "descartar"


def test_red_flags_with_dudar_ok() -> None:
    ev = _sample(red_flags_match=["sin_contrato_indefinido"], recomendacion="dudar")
    assert ev.recomendacion == "dudar"


def test_red_flags_with_aplicar_raises() -> None:
    with pytest.raises(ValidationError, match="aplicar"):
        _sample(red_flags_match=["sin_contrato_indefinido"], recomendacion="aplicar")


def test_empty_red_flags_with_aplicar_ok() -> None:
    ev = _sample(red_flags_match=[], recomendacion="aplicar")
    assert ev.recomendacion == "aplicar"


# ---------------------------------------------------------------------------
# List item stripping
# ---------------------------------------------------------------------------


def test_ventajas_items_stripped() -> None:
    ev = _sample(ventajas=["  Stack moderno  ", "  Remoto  "])
    assert ev.ventajas == ["Stack moderno", "Remoto"]


def test_blank_items_dropped() -> None:
    ev = _sample(ventajas=["Remoto", "   ", "Stack"])
    assert ev.ventajas == ["Remoto", "Stack"]


# ---------------------------------------------------------------------------
# to_db_row
# ---------------------------------------------------------------------------


def test_to_db_row_fields() -> None:
    ev = _sample(
        score=80,
        ventajas=["Buen stack", "Remoto"],
        desventajas=["Salario bajo"],
        red_flags_match=["startup_sin_financiacion"],
        recomendacion="dudar",
        reasoning="Interesante pero con dudas salariales.",
    )
    row = ev.to_db_row(offer_id=42)

    assert row.offer_id == 42
    assert row.puntuacion == 80
    assert row.pros == ["Buen stack", "Remoto"]
    assert row.contras == {
        "desventajas": ["Salario bajo"],
        "red_flags_match": ["startup_sin_financiacion"],
    }
    assert row.recomendacion == "dudar"
    assert row.razonamiento == "Interesante pero con dudas salariales."


def test_to_db_row_type() -> None:
    from src.db.models import Evaluation as DbEvaluation

    row = _sample().to_db_row(offer_id=1)
    assert isinstance(row, DbEvaluation)


def test_to_db_row_no_red_flags() -> None:
    ev = _sample(red_flags_match=[])
    row = ev.to_db_row(offer_id=5)
    assert row.contras["red_flags_match"] == []


# ---------------------------------------------------------------------------
# Invalid recomendacion value
# ---------------------------------------------------------------------------


def test_invalid_recomendacion_raises() -> None:
    with pytest.raises(ValidationError):
        _sample(recomendacion="solicitar")  # not in Literal
