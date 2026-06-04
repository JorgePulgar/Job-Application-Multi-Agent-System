"""Integration test: full orchestrator pipeline with mocked agents."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.orchestrator as orch_module
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Company, Evaluation, Offer, RunLog, User
from src.models.draft import Draft
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.orchestrator import Orchestrator, RunResult

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_GOOD_BODY = (
    "Construí un pipeline con Kafka que procesa millones de eventos al día. "
    "En TechCorp trabajáis con ese tipo de stack, así que el problema lo conozco bien. "
    "Trabajo a diario con Python y SQL. Puedo enviaros un recorrido de dos minutos por "
    "el repositorio, o lo vemos en una llamada corta cuando queráis."
)

_MOCK_CLIENT = MagicMock()


def _make_profile(username: str = "jorge") -> UserProfile:
    return UserProfile(
        username=username,
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["ML Engineer"],
        tech_stack=["Python"],
        red_flags=[],
        min_salary=40000,
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="CV de prueba.",
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
def seeded_evaluada(db_engine: Any) -> None:
    """Seed: 1 user, 1 company, 2 evaluada offers with aplicar evaluations."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()

        co = Company(nombre="TechCorp", sector="software", descripcion="Software company.")
        session.add(co)
        session.flush()

        for i in range(2):
            offer = Offer(
                user_id=user.id,
                company_id=co.id,
                titulo=f"ML Engineer {i}",
                empresa="TechCorp",
                fuente="adzuna",
                hash_unico=f"pipe{i:03d}",
                estado=OfferEstado.evaluada,
                descripcion="Rol ML.",
            )
            session.add(offer)
            session.flush()
            session.add(
                Evaluation(
                    offer_id=offer.id,
                    puntuacion=80,
                    pros=["Stack relevante"],
                    contras={"desventajas": [], "red_flags_match": []},
                    recomendacion="aplicar",
                    razonamiento="OK.",
                )
            )
        session.commit()


@pytest.fixture()
def patch_session(db_engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _fake() -> Generator[Session, None, None]:
        with Session(db_engine) as s:
            yield s
            s.commit()

    monkeypatch.setattr(orch_module, "get_session", _fake)


@pytest.fixture()
def patch_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orch_module, "load_profile", lambda u: _make_profile(u))
    monkeypatch.setattr(orch_module, "upsert_user_row", lambda *_a, **_kw: None)
    monkeypatch.setattr(orch_module, "AzureOpenAIClient", lambda **_kw: _MOCK_CLIENT)


# ---------------------------------------------------------------------------
# Tests: write stage (evaluate already done in seed)
# ---------------------------------------------------------------------------


def test_pipeline_writes_drafts_and_returns_correct_counts(
    seeded_evaluada: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
) -> None:
    """Write stage produces 2 drafts; RunResult has success=True."""
    good_draft = Draft(
        email_subject="ML Engineer en TechCorp",
        email_body=_GOOD_BODY,
        experiencias_destacadas=["Kafka pipeline", "Python", "SQL"],
    )

    with (
        patch(
            "src.agents.application_writer.ApplicationWriter.write", new_callable=AsyncMock
        ) as mock_write,
        patch("src.services.draft_persistence.save_draft", return_value=Path(".")),
        patch("src.agents.application_writer.prompt_loader"),
    ):
        mock_write.return_value = good_draft

        orch = Orchestrator(skip_stages=frozenset({"scrape", "filter", "research", "evaluate"}))
        result: RunResult = asyncio.run(orch.run_for_user("jorge"))

    assert result.success is True
    assert result.fatal_error is None
    assert result.drafts_generados == 2
    assert result.errores == []

    with Session(db_engine) as session:
        run_logs = list(session.execute(select(RunLog)).scalars())
    assert len(run_logs) == 1
    assert run_logs[0].borradores_generados == 2
    assert run_logs[0].estado == "completed"


def test_pipeline_run_result_mirrors_run_log(
    seeded_evaluada: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
) -> None:
    """RunResult.drafts_generados must equal run_logs.borradores_generados."""
    good_draft = Draft(
        email_subject="ML Engineer en TechCorp",
        email_body=_GOOD_BODY,
        experiencias_destacadas=["Kafka pipeline", "Python", "SQL"],
    )

    with (
        patch(
            "src.agents.application_writer.ApplicationWriter.write", new_callable=AsyncMock
        ) as mock_write,
        patch("src.services.draft_persistence.save_draft", return_value=Path(".")),
        patch("src.agents.application_writer.prompt_loader"),
    ):
        mock_write.return_value = good_draft

        orch = Orchestrator(skip_stages=frozenset({"scrape", "filter", "research", "evaluate"}))
        result = asyncio.run(orch.run_for_user("jorge"))

    with Session(db_engine) as session:
        row = session.execute(select(RunLog)).scalar_one()

    assert row.borradores_generados == result.drafts_generados


def test_run_for_all_users_returns_one_result_per_user(
    seeded_evaluada: None,
    patch_session: None,
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_for_all_users iterates all YAML files in config_path."""
    (tmp_path / "usera.yaml").write_text("dummy\n")
    (tmp_path / "userb.yaml").write_text("dummy\n")

    profiles = {
        "usera": _make_profile("usera"),
        "userb": _make_profile("userb"),
    }
    monkeypatch.setattr(orch_module, "load_profile", lambda u: profiles[u])
    monkeypatch.setattr(orch_module, "upsert_user_row", lambda *_a, **_kw: None)
    monkeypatch.setattr(orch_module, "AzureOpenAIClient", lambda **_kw: _MOCK_CLIENT)

    orch = Orchestrator(
        skip_stages=frozenset({"scrape", "filter", "research", "evaluate", "write"}),
        config_path=tmp_path,
    )
    results = asyncio.run(orch.run_for_all_users())

    assert len(results) == 2
    assert {r.username for r in results} == {"usera", "userb"}
