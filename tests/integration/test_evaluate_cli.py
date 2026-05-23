"""Integration tests for `python -m src.cli evaluate` using a real in-memory SQLite DB."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.cli as cli_module
from src.cli import cli
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Company, Evaluation, Offer, User
from src.models.evaluation import ViabilityEvaluation
from src.services.azure_openai import ChatResult, TokenUsage

# ---------------------------------------------------------------------------
# LLM response helpers
# ---------------------------------------------------------------------------


def _make_evaluation(recomendacion: str = "aplicar", score: int = 80) -> ViabilityEvaluation:
    return ViabilityEvaluation(
        score=score,
        ventajas=["Buen stack", "Sector objetivo"],
        desventajas=[],
        red_flags_match=[],
        recomendacion=recomendacion,  # type: ignore[arg-type]
        reasoning="Evaluación de prueba.",
    )


def _make_chat_result(evaluation: ViabilityEvaluation) -> ChatResult:
    return ChatResult(
        content="",
        parsed=evaluation,
        usage=TokenUsage(
            prompt_tokens=400, cached_tokens=200, completion_tokens=120, total_tokens=520
        ),
        latency_ms=700.0,
        model="gpt-4o",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def seeded_db(db_engine: Any) -> None:
    """Seed: 1 user, 2 companies, 3 investigada offers (2 for co1, 1 for co2)."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()

        co1 = Company(nombre="Alpha SL", sector="fintech", descripcion="Fintech startup.")
        co2 = Company(nombre="Beta SA", sector="saas", descripcion="SaaS platform.")
        session.add_all([co1, co2])
        session.flush()

        session.add_all(
            [
                Offer(
                    user_id=user.id,
                    company_id=co1.id,
                    titulo="ML Engineer",
                    empresa="Alpha SL",
                    fuente="adzuna",
                    hash_unico="a001",
                    estado=OfferEstado.investigada,
                    descripcion="Rol ML en fintech.",
                ),
                Offer(
                    user_id=user.id,
                    company_id=co1.id,
                    titulo="Data Scientist",
                    empresa="Alpha SL",
                    fuente="adzuna",
                    hash_unico="a002",
                    estado=OfferEstado.investigada,
                    descripcion="Rol DS en fintech.",
                ),
                Offer(
                    user_id=user.id,
                    company_id=co2.id,
                    titulo="Backend Engineer",
                    empresa="Beta SA",
                    fuente="jooble",
                    hash_unico="b001",
                    estado=OfferEstado.investigada,
                    descripcion="Rol backend.",
                ),
            ]
        )
        session.commit()


@pytest.fixture()
def patch_get_session(db_engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _fake() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session
            session.commit()

    monkeypatch.setattr(cli_module, "get_session", _fake)


@pytest.fixture()
def mock_llm_client() -> MagicMock:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_evaluation("aplicar")))
    return client


@pytest.fixture()
def patch_azure_client(mock_llm_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "AzureOpenAIClient", lambda: mock_llm_client)


@pytest.fixture()
def mock_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.models.user_profile import LocationPreference, Modality, UserProfile

    profile = UserProfile(
        username="jorge",
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["ML Engineer", "Data Scientist"],
        tech_stack=["Python", "TensorFlow"],
        red_flags=["presencial obligatorio"],
        min_salary=40000,
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="Resumen de prueba.",
    )
    monkeypatch.setattr(cli_module, "load_profile", lambda _: profile)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_evaluate_runs_for_all_investigada_offers(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
) -> None:
    """3 investigada offers → 3 LLM calls."""
    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        result = CliRunner().invoke(cli, ["evaluate", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert mock_llm_client.chat.await_count == 3


def test_evaluate_transitions_offer_estado_to_evaluada(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    """All 3 offers should be in estado=evaluada after the run."""
    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        result = CliRunner().invoke(cli, ["evaluate", "--user", "jorge"])

    assert result.exit_code == 0, result.output

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars().all())

    for offer in offers:
        assert offer.estado == OfferEstado.evaluada, (
            f"offer '{offer.titulo}' has estado='{offer.estado}', expected 'evaluada'"
        )


def test_evaluate_creates_evaluation_rows(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    """One Evaluation row per offer should be created."""
    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        CliRunner().invoke(cli, ["evaluate", "--user", "jorge"])

    with Session(db_engine) as session:
        evals = list(session.execute(select(Evaluation)).scalars().all())

    assert len(evals) == 3


def test_evaluate_sets_razon_descarte_for_descartar(
    seeded_db: None,
    patch_get_session: None,
    mock_profile: None,
    monkeypatch: pytest.MonkeyPatch,
    db_engine: Any,
) -> None:
    """Offers evaluated as 'descartar' must have razon_descarte populated."""
    descartar_eval = _make_evaluation("descartar", score=10)
    descartar_eval = ViabilityEvaluation(
        score=10,
        ventajas=["Remoto"],
        desventajas=["Rol incorrecto"],
        red_flags_match=["presencial obligatorio"],
        recomendacion="descartar",
        reasoning="No encaja con el perfil del candidato.",
    )
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(descartar_eval))
    monkeypatch.setattr(cli_module, "AzureOpenAIClient", lambda: client)

    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        result = CliRunner().invoke(cli, ["evaluate", "--user", "jorge"])

    assert result.exit_code == 0, result.output

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars().all())

    for offer in offers:
        assert offer.razon_descarte is not None, (
            f"offer '{offer.titulo}' should have razon_descarte set"
        )
        assert "No encaja" in offer.razon_descarte


def test_evaluate_limit_flag(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
) -> None:
    """--limit 1 should only process 1 offer."""
    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        result = CliRunner().invoke(cli, ["evaluate", "--user", "jorge", "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert mock_llm_client.chat.await_count == 1


def test_evaluate_dry_run_does_not_write(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    """--dry-run must not write any Evaluation rows or change offer estado."""
    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        result = CliRunner().invoke(cli, ["evaluate", "--dry-run", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output

    with Session(db_engine) as session:
        evals = list(session.execute(select(Evaluation)).scalars().all())
        offers = list(session.execute(select(Offer)).scalars().all())

    assert evals == []
    for offer in offers:
        assert offer.estado == OfferEstado.investigada


def test_evaluate_summary_shows_recommendation_counts(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.return_value = "user"
        result = CliRunner().invoke(cli, ["evaluate", "--user", "jorge"])

    assert "Aplicar" in result.output
    assert "Dudar" in result.output
    assert "Descartar" in result.output


def test_evaluate_unknown_user_exits_gracefully(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    result = CliRunner().invoke(cli, ["evaluate", "--user", "unknownuser"])
    assert result.exit_code == 0
    assert "not found in DB" in result.output


def test_evaluate_no_offers_exits_gracefully(
    db_engine: Any,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    """No investigada offers → informative message, no crash."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.commit()

    with patch("src.agents.viability_evaluator.prompt_loader"):
        result = CliRunner().invoke(cli, ["evaluate", "--user", "jorge"])

    assert result.exit_code == 0
    assert "No hay" in result.output
