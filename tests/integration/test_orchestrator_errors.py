"""Integration test: per-offer error handling in the orchestrator."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.orchestrator as orch_module
from src.agents.viability_evaluator import ViabilityEvaluator
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Company, Offer, RunLog, User
from src.models.evaluation import ViabilityEvaluation
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.orchestrator import Orchestrator

_MOCK_CLIENT = MagicMock()


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
        cv_summary="CV de prueba.",
    )


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def seeded_db(db_engine: Any) -> None:
    """Seed: 1 user, 1 company, 3 investigada offers."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()

        co = Company(nombre="TechCorp", sector="software", descripcion="Co.")
        session.add(co)
        session.flush()

        for i in range(3):
            session.add(
                Offer(
                    user_id=user.id,
                    company_id=co.id,
                    titulo=f"ML Engineer {i}",
                    empresa="TechCorp",
                    fuente="adzuna",
                    hash_unico=f"errtest{i:03d}",
                    estado=OfferEstado.investigada,
                    descripcion="Rol ML.",
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


def test_failing_offer_moves_to_error_others_continue(
    seeded_db: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
) -> None:
    """One offer failing during evaluate must not block the other two."""
    call_count = [0]

    async def _flaky(self: Any, offer: Offer, company: Any, profile: Any) -> ViabilityEvaluation:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("simulated LLM failure")
        ev = ViabilityEvaluation(
            score=70,
            ventajas=["Stack ok"],
            desventajas=[],
            red_flags_match=[],
            recomendacion="aplicar",
            reasoning="OK.",
        )
        self._session.add(ev.to_db_row(offer_id=offer.id))
        offer.estado = OfferEstado.evaluada
        self._session.flush()
        return ev

    with (
        patch.object(ViabilityEvaluator, "evaluate", new=_flaky),
        patch("src.agents.viability_evaluator.prompt_loader"),
    ):
        orch = Orchestrator(skip_stages=frozenset({"scrape", "filter", "research", "write"}))
        result = asyncio.run(orch.run_for_user("jorge"))

    assert result.success is True  # run-level success despite per-offer error
    assert len(result.errores) == 1
    assert result.errores[0]["stage"] == "evaluate"
    assert result.errores[0]["error_class"] == "RuntimeError"

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars())

    error_offers = [o for o in offers if o.estado == OfferEstado.error]
    evaluada_offers = [o for o in offers if o.estado == OfferEstado.evaluada]

    assert len(error_offers) == 1
    assert error_offers[0].error_note is not None
    assert "RuntimeError" in error_offers[0].error_note
    assert len(evaluada_offers) == 2


def test_error_offer_has_error_note_populated(
    seeded_db: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
) -> None:
    """error_note must contain the exception class and message."""

    async def _always_fail(
        self: Any, offer: Offer, company: Any, profile: Any
    ) -> ViabilityEvaluation:
        raise ValueError("test error message")

    with (
        patch.object(ViabilityEvaluator, "evaluate", new=_always_fail),
        patch("src.agents.viability_evaluator.prompt_loader"),
    ):
        orch = Orchestrator(skip_stages=frozenset({"scrape", "filter", "research", "write"}))
        asyncio.run(orch.run_for_user("jorge"))

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars())

    for offer in offers:
        assert offer.estado == OfferEstado.error
        assert offer.error_note is not None
        assert "ValueError" in offer.error_note
        assert "test error message" in offer.error_note


def test_fatal_error_writes_failed_run_log(
    seeded_db: None,
    patch_session: None,
    patch_profile: None,
    db_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fatal exception must still produce a run_logs row with estado=failed."""

    async def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise ConnectionError("DB connection lost")

    monkeypatch.setattr(orch_module, "run_scrape", _boom)

    orch = Orchestrator()
    result = asyncio.run(orch.run_for_user("jorge"))

    assert result.success is False
    assert result.fatal_error is not None
    assert "ConnectionError" in result.fatal_error

    with Session(db_engine) as session:
        run_logs = list(session.execute(select(RunLog)).scalars())

    assert len(run_logs) == 1
    assert run_logs[0].estado == "failed"
    assert run_logs[0].errores is not None
