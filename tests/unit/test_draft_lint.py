"""Unit tests for src/services/draft_lint.py."""

from __future__ import annotations

from src.models.company import CompanyDossier
from src.models.draft import Draft
from src.services import draft_lint

_EMPRESA = "Acme Corp"

# A clean, >=200 char body that names the company and cites a dossier fact (Kafka).
_CLEAN_BODY = (
    "Construí un pipeline de ingestión con Kafka que procesa millones de eventos "
    "al día. Vi que en Acme trabajáis justo con ese stack, así que el problema lo "
    "conozco bien. Trabajo a diario con Python y SQL. Os puedo enviar un recorrido "
    "de 2 minutos por el repositorio, o lo vemos en una llamada corta."
)


def _dossier(**overrides: object) -> CompanyDossier:
    data: dict[str, object] = {
        "sector": "fintech",
        "ubicacion_hq": "Madrid, España",
        "descripcion": "Plataforma de pagos en tiempo real.",
        "stack_tecnologico": ["Kafka", "Python"],
        "productos_o_servicios": ["plataforma de pagos"],
    }
    data.update(overrides)
    return CompanyDossier.model_validate(data)


def _draft(body: str = _CLEAN_BODY, **overrides: object) -> Draft:
    data: dict[str, object] = {
        "email_subject": "ingeniero de datos para Acme, con pruebas",
        "email_body": body,
        "carta_presentacion": None,
        "experiencias_destacadas": ["Kafka pipeline", "Python", "SQL"],
        "needs_manual_context": False,
        "flagged_reasons": [],
    }
    data.update(overrides)
    return Draft.model_validate(data)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_clean_draft_passes() -> None:
    result = draft_lint.lint(_draft(), _dossier(), _EMPRESA)
    assert result.ok
    assert result.issues == []


def test_flagged_draft_is_ok() -> None:
    """A model self-flagged draft is an intentional placeholder, not a failure."""
    flagged = Draft(
        email_subject="",
        email_body="",
        needs_manual_context=True,
        flagged_reasons=["no_hook"],
        experiencias_destacadas=["a", "b", "c"],
    )
    assert draft_lint.lint(flagged, _dossier(), _EMPRESA).ok


# ---------------------------------------------------------------------------
# Prohibited words (accent-folded, word-boundary)
# ---------------------------------------------------------------------------


def test_prohibited_word_spanish() -> None:
    body = _CLEAN_BODY + " Soy una persona apasionada del dato."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("apasionada" in i for i in result.issues)


def test_prohibited_word_accent_folded() -> None:
    """'dinamico' without accent must still match 'dinámico'."""
    body = _CLEAN_BODY + " Trabajo en un entorno dinamico."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("dinámico" in i for i in result.issues)


def test_prohibited_word_english() -> None:
    body = _CLEAN_BODY + " I leverage modern tooling."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("leverage" in i for i in result.issues)


def test_english_tell_does_not_match_inside_spanish_word() -> None:
    """'realm' must not match inside 'realmente' (word-boundary matching)."""
    body = _CLEAN_BODY + " Esto encaja realmente bien con mi experiencia."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert result.ok, result.issues


def test_prohibited_phrase() -> None:
    body = _CLEAN_BODY + " Soy un jugador de equipo."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("jugador de equipo" in i for i in result.issues)


# ---------------------------------------------------------------------------
# Dashes (strictest rule)
# ---------------------------------------------------------------------------


def test_em_dash_fails() -> None:
    body = _CLEAN_BODY + " Trabajo con Python — y con Kafka."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("raya" in i for i in result.issues)


def test_en_dash_fails() -> None:
    body = _CLEAN_BODY + " Rango 2020 – 2024."  # noqa: RUF001
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("guion largo" in i for i in result.issues)


def test_dash_in_subject_fails() -> None:
    result = draft_lint.lint(
        _draft(email_subject="ingeniero de datos — Acme"), _dossier(), _EMPRESA
    )
    assert not result.ok


# ---------------------------------------------------------------------------
# Specificity
# ---------------------------------------------------------------------------


def test_specificity_missing_company_name() -> None:
    body = (
        "Construí un pipeline de ingestión con Kafka que procesa millones de eventos al día. "
        "Trabajo a diario con Python y SQL y me ocupo de la calidad del dato. Puedo enviaros un "
        "recorrido de 2 minutos por el repositorio o lo vemos en una llamada corta de 15 minutos."
    )
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("no menciona a la empresa" in i for i in result.issues)


def test_specificity_name_but_no_fact() -> None:
    body = (
        "Construí sistemas de datos durante varios años y me ocupo de su calidad. En Acme me "
        "gustaría seguir con ese tipo de trabajo porque encaja con lo que hago. Puedo enviaros "
        "un recorrido de 2 minutos por el repositorio o lo vemos en una llamada corta de 15 min."
    )
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("dato concreto" in i for i in result.issues)


def test_specificity_skipped_without_dossier() -> None:
    """With no dossier, only the company-name reference is required."""
    body = (
        "Construí sistemas de datos durante varios años. En Acme me gustaría seguir con ese tipo "
        "de trabajo porque encaja con lo que hago a diario. Puedo enviaros un recorrido de 2 "
        "minutos por el repositorio, o lo vemos en una llamada corta de quince minutos."
    )
    result = draft_lint.lint(_draft(body=body), None, _EMPRESA)
    assert result.ok, result.issues


# ---------------------------------------------------------------------------
# AI disclosure
# ---------------------------------------------------------------------------


def test_ai_disclosure_fails() -> None:
    body = _CLEAN_BODY + " Este correo ha sido generado por una IA."
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert not result.ok
    assert any("asistencia de IA" in i for i in result.issues)


def test_legit_ai_mention_passes() -> None:
    """Describing AI work is not a disclosure of AI assistance."""
    body = (
        "Soy ingeniero de IA y construí un pipeline con Kafka en Acme-style workloads. Trabajo "
        "con Python a diario y entreno modelos en producción. Puedo enviaros un recorrido de 2 "
        "minutos por el repositorio o lo vemos en una llamada corta. Menciono Acme y Kafka."
    )
    result = draft_lint.lint(_draft(body=body), _dossier(), _EMPRESA)
    assert result.ok, result.issues


# ---------------------------------------------------------------------------
# body_hash helper
# ---------------------------------------------------------------------------


def test_body_hash_is_stable_and_short() -> None:
    h1 = draft_lint.body_hash("hola")
    h2 = draft_lint.body_hash("hola")
    assert h1 == h2
    assert len(h1) == 12


# ---------------------------------------------------------------------------
# No draft body leaks into logs
# ---------------------------------------------------------------------------


def test_lint_does_not_log_draft_body() -> None:
    from structlog.testing import capture_logs

    draft = _draft()  # body contains the distinctive token "Kafka"
    with capture_logs() as logs:
        draft_lint.lint(draft, _dossier(), _EMPRESA)

    events = [e for e in logs if e.get("event") == "draft_lint"]
    assert events, "expected a draft_lint log event"
    ev = events[0]
    assert "body_hash" in ev
    blob = " ".join(str(v) for v in ev.values())
    assert draft.email_body not in blob
    assert "Kafka" not in blob  # distinctive body token must not leak
