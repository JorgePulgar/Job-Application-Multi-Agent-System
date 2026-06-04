"""Integration test: run_logs row is always written after orchestrator run."""

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
from src.orchestrator import Orchestrator

_MOCK_CLIENT = MagicMock()

_GOOD_BODY = (
    "Construí un pipeline con Kafka que procesa millones de eventos al día. "
    "En Alpha trabajáis con ese tipo de stack, así que el problema lo conozco bien. "
    "Trabajo a diario con Python y SQL. Puedo enviaros un recorrido de dos minutos por "
    "el repositorio, o lo vemos en una llamada corta cuando queráis."
)


def _make_profile() -> UserProfile:
    return UserProfile(
        username="jorge",
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["ML Engineer"],
        tech_stack=["Python"],
        red_flags=[],
        min_salary=40000,
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="CV.",
    )


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def seeded_evaluada(db_engine: Any) -> None:
    """Seed: 1 user, 1 company, 1 evaluada offer with aplicar evaluation."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()
        co = Company(nombre="Alpha", sector="tech", descripcion="Tech co.")
        session.add(co)
        session.flush()
        offer = Offer(
            user_id=user.id,
            company_id=co.id,
            titulo="ML Engineer",
            empresa="Alpha",
            fuente="adzuna",
            hash_unico="rl001",
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
    monkeypatch.setattr(orch_module, "load_profile", lambda _: _make_profile())
    monkeypatch.setattr(orch_module, "upsert_user_row", lambda *_a, **_kw: None)
    monkeypatch.setattr(orch_module, "AzureOpenAIClient", lambda **_kw: _MOCK_CLIENT)


def test_exactly_one_run_log_row_written(
    seeded_evaluada: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
) -> None:
    """Exactly one run_logs row must exist after a successful pipeline run."""
    good_draft = Draft(
        email_subject="ML Engineer en Alpha",
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
        asyncio.run(orch.run_for_user("jorge"))

    with Session(db_engine) as session:
        rows = list(session.execute(select(RunLog)).scalars())

    assert len(rows) == 1


def test_run_log_counts_match_pipeline_output(
    seeded_evaluada: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
) -> None:
    """run_logs.borradores_generados must equal RunResult.drafts_generados."""
    good_draft = Draft(
        email_subject="ML Engineer",
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
    assert row.fecha_inicio is not None
    assert row.fecha_fin is not None


def test_run_log_written_even_on_fatal_error(
    seeded_evaluada: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fatal error must still produce a run_logs row with estado=failed."""

    async def _boom(*_args: Any, **_kw: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(orch_module, "run_scrape", _boom)

    orch = Orchestrator()
    result = asyncio.run(orch.run_for_user("jorge"))

    assert result.success is False

    with Session(db_engine) as session:
        rows = list(session.execute(select(RunLog)).scalars())

    assert len(rows) == 1
    assert rows[0].estado == "failed"
