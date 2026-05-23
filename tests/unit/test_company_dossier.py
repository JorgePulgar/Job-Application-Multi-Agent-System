"""Unit tests for src/models/company.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.company import CompanyDossier, TamanoEmpresa


def _sample_dossier(**overrides: object) -> CompanyDossier:
    data: dict[str, object] = {
        "sector": "fintech",
        "tamano": TamanoEmpresa.startup,
        "ubicacion_hq": "Madrid, España",
        "descripcion": "Plataforma de pagos para el mercado latinoamericano.",
        "stack_tecnologico": ["Python", "Kubernetes", "PostgreSQL"],
        "cultura_notas": ["Trabajo remoto primero.", "Reuniones asíncronas."],
        "red_flags_detectadas": [],
        "productos_o_servicios": ["API de pagos", "Dashboard de analítica"],
        "equipo_ai_detectado": True,
        "fuentes": ["https://example.com", "https://linkedin.com/company/example"],
    }
    data.update(overrides)
    return CompanyDossier.model_validate(data)


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_round_trip_json() -> None:
    dossier = _sample_dossier()
    dumped = dossier.model_dump(mode="json")
    restored = CompanyDossier.model_validate(dumped)
    assert restored.sector == dossier.sector
    assert restored.tamano == dossier.tamano
    assert restored.stack_tecnologico == dossier.stack_tecnologico
    assert restored.equipo_ai_detectado == dossier.equipo_ai_detectado


# ---------------------------------------------------------------------------
# Stack dedup and lowercase
# ---------------------------------------------------------------------------


def test_stack_lowercased() -> None:
    dossier = _sample_dossier(stack_tecnologico=["Python", "PYTHON", "python", "TensorFlow"])
    assert dossier.stack_tecnologico == ["python", "tensorflow"]


def test_stack_deduped_preserves_order() -> None:
    dossier = _sample_dossier(stack_tecnologico=["go", "rust", "go", "python"])
    assert dossier.stack_tecnologico == ["go", "rust", "python"]


def test_stack_strips_whitespace() -> None:
    dossier = _sample_dossier(stack_tecnologico=["  python  ", "rust"])
    assert dossier.stack_tecnologico == ["python", "rust"]


# ---------------------------------------------------------------------------
# Other list dedup
# ---------------------------------------------------------------------------


def test_cultura_notas_deduped() -> None:
    dossier = _sample_dossier(cultura_notas=["Remoto primero.", "Remoto primero.", "Flexible."])
    assert dossier.cultura_notas == ["Remoto primero.", "Flexible."]


def test_red_flags_deduped() -> None:
    dossier = _sample_dossier(red_flags_detectadas=["Layoffs 2023.", "Layoffs 2023."])
    assert dossier.red_flags_detectadas == ["Layoffs 2023."]


def test_productos_deduped() -> None:
    dossier = _sample_dossier(productos_o_servicios=["API", "API", "Dashboard"])
    assert dossier.productos_o_servicios == ["API", "Dashboard"]


def test_cultura_notas_preserves_case() -> None:
    dossier = _sample_dossier(cultura_notas=["Trabajo Remoto.", "trabajo remoto."])
    # Different casing → not deduped; both preserved
    assert len(dossier.cultura_notas) == 2


# ---------------------------------------------------------------------------
# to_summary_for_prompt
# ---------------------------------------------------------------------------


def test_summary_contains_key_fields() -> None:
    dossier = _sample_dossier()
    summary = dossier.to_summary_for_prompt()
    assert "fintech" in summary
    assert "Madrid" in summary
    assert "python" in summary
    assert "Sí" in summary  # equipo_ai_detectado = True


def test_summary_within_token_budget() -> None:
    dossier = _sample_dossier()
    summary = dossier.to_summary_for_prompt()
    # ~4 chars per token; 300 tokens ≈ 1200 chars; allow 20% margin
    assert len(summary) <= 1440, f"Summary too long: {len(summary)} chars"


def test_summary_truncates_long_descripcion() -> None:
    long_desc = "x" * 800
    dossier = _sample_dossier(descripcion=long_desc)
    summary = dossier.to_summary_for_prompt()
    assert "…" in summary


def test_summary_no_red_flags_shows_ninguna() -> None:
    dossier = _sample_dossier(red_flags_detectadas=[])
    summary = dossier.to_summary_for_prompt()
    assert "Ninguna" in summary


def test_summary_no_ai_team_shows_no() -> None:
    dossier = _sample_dossier(equipo_ai_detectado=False)
    summary = dossier.to_summary_for_prompt()
    assert "No" in summary


# ---------------------------------------------------------------------------
# Fuentes (HttpUrl)
# ---------------------------------------------------------------------------


def test_fuentes_are_valid_urls() -> None:
    dossier = _sample_dossier(fuentes=["https://acme.com/about", "https://glassdoor.com/acme"])
    assert len(dossier.fuentes) == 2


def test_invalid_url_raises() -> None:
    with pytest.raises(ValidationError):
        _sample_dossier(fuentes=["not-a-url"])


# ---------------------------------------------------------------------------
# Tamano enum
# ---------------------------------------------------------------------------


def test_tamano_defaults_to_unknown() -> None:
    data = {
        "sector": "saas",
        "ubicacion_hq": "Barcelona",
        "descripcion": "SaaS company.",
    }
    dossier = CompanyDossier.model_validate(data)
    assert dossier.tamano == TamanoEmpresa.unknown


def test_tamano_all_values_accepted() -> None:
    for val in TamanoEmpresa:
        dossier = _sample_dossier(tamano=val)
        assert dossier.tamano == val
