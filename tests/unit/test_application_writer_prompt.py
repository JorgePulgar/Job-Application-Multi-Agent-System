"""Unit tests for the application_writer prompt templates."""

from __future__ import annotations

import re

from src.services import prompt_loader

# Prohibited words/phrases that must never appear in a generated draft.
_PROHIBITED = [
    # Spanish AI-tells / clichés
    "apasionado",
    "apasionada",
    "proactivo",
    "proactiva",
    "jugador de equipo",
    "orientado a resultados",
    "orientada a resultados",
    "sinergia",
    "sin fisuras",
    "ritmo frenético",
    # English AI-tells
    "leverage",
    "robust",
    "seamless",
    "passionate",
    "synergy",
    "showcase",
    "delve",
]

# Em-dash and en-dash: the strictest rule. Must not appear in model-facing examples.
_DASHES = ["—", "–"]  # em-dash, en-dash  # noqa: RUF001

_USER_VARS = {
    "titulo": "Data Engineer",
    "empresa": "Acme Corp",
    "ubicacion": "Madrid",
    "modalidad": "remote",
    "descripcion": "Construir pipelines de datos.",
    "dossier_summary": "Empresa fintech con plataforma de pagos.",
    "evaluation_ventajas": "- Stack alineado",
    "evaluation_desventajas": "- (ninguno)",
    "target_roles": "Data Engineer, ML Engineer",
}


def _fenced_blocks(text: str) -> str:
    """Return the concatenation of all fenced code blocks (the few-shot examples)."""
    return "\n".join(re.findall(r"```.*?```", text, flags=re.DOTALL))


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def test_system_contains_prohibited_words_list() -> None:
    """The prompt must list the prohibited words so the model knows to avoid them."""
    system = prompt_loader.load_system("application_writer", cv_summary="CV de prueba.")
    lowered = system.lower()
    for word in [
        "apasionado",
        "proactivo",
        "jugador de equipo",
        "orientado a resultados",
        "leverage",
        "seamless",
        "passionate",
    ]:
        assert word in lowered, f"prohibited word '{word}' not listed in system prompt"


def test_system_states_zero_dashes_rule() -> None:
    """The strictest rule (no em/en-dashes) must be encoded in the prompt."""
    system = prompt_loader.load_system("application_writer", cv_summary="CV.").lower()
    assert "raya" in system  # "cero rayas" rule
    assert "90" in system and "160" in system  # word-count range


def test_system_interpolates_cv() -> None:
    system = prompt_loader.load_system("application_writer", cv_summary="MARCADOR_CV_123")
    assert "MARCADOR_CV_123" in system


def test_examples_contain_no_prohibited_words() -> None:
    """The few-shot examples (model-facing output) must be clean of prohibited words."""
    system = prompt_loader.load_system("application_writer", cv_summary="CV.")
    examples = _fenced_blocks(system).lower()
    assert examples, "system prompt has no fenced few-shot examples"
    for word in _PROHIBITED:
        assert word not in examples, f"example contains prohibited word '{word}'"


def test_examples_contain_no_dashes() -> None:
    """Few-shot examples must contain zero em-dashes or en-dashes (strictest rule)."""
    system = prompt_loader.load_system("application_writer", cv_summary="CV.")
    examples = _fenced_blocks(system)
    assert examples
    for dash in _DASHES:
        assert dash not in examples, f"example contains banned dash '{dash}'"


def test_system_states_no_ai_disclosure() -> None:
    system = prompt_loader.load_system("application_writer", cv_summary="CV.").lower()
    assert "ia" in system and "needs_manual_context" in system


# ---------------------------------------------------------------------------
# User prompt
# ---------------------------------------------------------------------------


def test_user_interpolates_all_variables() -> None:
    """All declared variables resolve without leaving unresolved placeholders."""
    user = prompt_loader.load_user("application_writer", **_USER_VARS)
    assert "{{" not in user
    for value in _USER_VARS.values():
        assert value in user


def test_user_prompt_has_no_dashes() -> None:
    """User prompt must be free of em/en-dashes."""
    user = prompt_loader.load_user("application_writer", **_USER_VARS)
    for dash in _DASHES:
        assert dash not in user


def test_user_declares_expected_placeholders() -> None:
    """Raw template must declare exactly the expected placeholder set."""
    from pathlib import Path

    path = Path("src/prompts/application_writer.user.md")
    raw = path.read_text(encoding="utf-8")
    found = set(re.findall(r"\{\{(\w+)\}\}", raw))
    assert found == set(_USER_VARS)
