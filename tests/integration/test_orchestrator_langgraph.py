"""Integration test: the feature-flagged LangGraph evaluate_and_draft path.

Covers Task 11: with the flag on, the orchestrator runs the subgraph per offer and
persists v1-shaped ``evaluations`` + ``drafts`` rows (so the dashboard/FastAPI
contract is unchanged); with the flag off, the v1 path is taken instead. The
subgraph internals are mocked here (they have their own tests) -- this isolates the
orchestrator integration + persistence.
"""

from __future__ import annotations

import asyncio
import contextlib
import types
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.orchestrator as orch_module
from src.db.base import Base
from src.db.enums import DraftEstado, OfferEstado
from src.db.models import Company, Evaluation, Offer, User
from src.db.models import Draft as DbDraft
from src.models.fit import CoverLetterDraft, FitAssessment
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.orchestrator import Orchestrator


def _profile(username: str = "jorge") -> UserProfile:
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
        cv_summary="CV.",
    )


def _fit(recommendation: str, score: int) -> FitAssessment:
    return FitAssessment(
        fit_level="strong" if recommendation == "apply" else "weak",
        recommendation=recommendation,  # type: ignore[arg-type]
        score=score,
        reasoning="Razón decisiva del encaje.",
        red_flags=[],
        missing_info=[],
        tailoring=None,
    )


class _FakeGraph:
    """Stand-in compiled graph: first ainvoke interrupts, aget_state returns state."""

    def __init__(self, values: dict[str, Any], *, interrupt: bool) -> None:
        self._values = values
        self._interrupt = interrupt
        self._calls = 0

    async def ainvoke(self, _input: Any, config: Any = None) -> dict[str, Any]:
        self._calls += 1
        if self._interrupt and self._calls == 1:
            return {"__interrupt__": [object()]}
        return {}

    async def aget_state(self, _config: Any) -> Any:
        snap = MagicMock()
        snap.values = self._values
        return snap


@contextlib.asynccontextmanager
async def _fake_open_checkpointer(*_a: Any, **_kw: Any) -> Any:
    yield MagicMock()


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def investigada_offer(db_engine: Any) -> int:
    """Seed one researched offer ready for the evaluate stage; return its id."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()
        co = Company(nombre="TechCorp", sector="software", descripcion="Software co.")
        session.add(co)
        session.flush()
        offer = Offer(
            user_id=user.id,
            company_id=co.id,
            titulo="ML Engineer",
            empresa="TechCorp",
            fuente="adzuna",
            hash_unico="lg-001",
            estado=OfferEstado.investigada,
            descripcion="Rol ML.",
        )
        session.add(offer)
        session.flush()
        offer_id = offer.id
        session.commit()
    return offer_id


def _run_graph_stage(db_engine: Any, offer_id: int, values: dict[str, Any], interrupt: bool) -> Any:
    """Invoke _eval_draft_graph for one seeded offer with a faked subgraph."""
    orch = Orchestrator()
    fake = _FakeGraph(values, interrupt=interrupt)
    with (
        Session(db_engine) as session,
        patch("src.graph.build.build_graph", return_value=fake),
        patch("src.graph.build.open_checkpointer", _fake_open_checkpointer),
    ):
        offer = session.get(Offer, offer_id)
        assert offer is not None
        errors: list[dict[str, Any]] = []
        counts = asyncio.run(
            orch._eval_draft_graph(session, _profile(), [offer], MagicMock(), errors)
        )
        session.commit()
    return counts, errors


def test_graph_apply_persists_eval_and_draft(db_engine: Any, investigada_offer: int) -> None:
    """apply verdict -> evaluations row (aplicar) + drafts row (pendiente) + borrador_generado."""
    values = {
        "fit": _fit("apply", 85),
        "draft": CoverLetterDraft(
            subject="ML Engineer en TechCorp",
            body="Cuerpo del correo con un dato concreto de TechCorp. " * 5,
            lead_angle="experiencia ML",
            hook="stack",
        ),
        "needs_manual_context": False,
    }
    (evaluated, shipped, manual), errors = _run_graph_stage(
        db_engine, investigada_offer, values, interrupt=True
    )
    assert (evaluated, shipped, manual) == (1, 1, 0)
    assert errors == []

    with Session(db_engine) as session:
        ev = session.scalars(select(Evaluation)).one()
        assert ev.puntuacion == 85
        assert ev.recomendacion == "aplicar"  # v1 dashboard vocabulary
        assert ev.razonamiento == "Razón decisiva del encaje."
        draft = session.scalars(select(DbDraft)).one()
        assert draft.estado == DraftEstado.pendiente
        assert draft.asunto == "ML Engineer en TechCorp"
        assert draft.cuerpo_email is not None
        offer = session.get(Offer, investigada_offer)
        assert offer is not None and offer.estado == OfferEstado.borrador_generado


def test_graph_skip_persists_eval_without_draft(db_engine: Any, investigada_offer: int) -> None:
    """skip verdict -> evaluations row (descartar) + razon_descarte, no draft, evaluada."""
    values = {"fit": _fit("skip", 30)}
    (evaluated, shipped, manual), errors = _run_graph_stage(
        db_engine, investigada_offer, values, interrupt=False
    )
    assert (evaluated, shipped, manual) == (1, 0, 0)
    assert errors == []

    with Session(db_engine) as session:
        ev = session.scalars(select(Evaluation)).one()
        assert ev.recomendacion == "descartar"
        assert session.scalars(select(DbDraft)).first() is None
        offer = session.get(Offer, investigada_offer)
        assert offer is not None
        assert offer.estado == OfferEstado.evaluada
        assert offer.razon_descarte


def test_graph_needs_manual_context(db_engine: Any, investigada_offer: int) -> None:
    """apply but no shippable draft -> draft row flagged, offer stays evaluada."""
    values = {"fit": _fit("apply", 70), "draft": None, "needs_manual_context": True}
    (evaluated, shipped, manual), _ = _run_graph_stage(
        db_engine, investigada_offer, values, interrupt=True
    )
    assert (evaluated, shipped, manual) == (1, 0, 1)

    with Session(db_engine) as session:
        draft = session.scalars(select(DbDraft)).one()
        assert draft.estado == DraftEstado.needs_manual_context
        assert draft.asunto is None
        offer = session.get(Offer, investigada_offer)
        assert offer is not None and offer.estado == OfferEstado.evaluada


# --- flag routing ----------------------------------------------------------


@pytest.fixture()
def patched_run(db_engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _fake_session() -> Generator[Session, None, None]:
        with Session(db_engine) as s:
            yield s
            s.commit()

    monkeypatch.setattr(orch_module, "get_session", _fake_session)
    monkeypatch.setattr(orch_module, "load_profile", lambda u: _profile(u))
    monkeypatch.setattr(orch_module, "upsert_user_row", lambda *_a, **_kw: None)
    monkeypatch.setattr(orch_module, "AzureOpenAIClient", lambda **_kw: MagicMock())


def _settings(flag: bool) -> Any:
    return lambda: types.SimpleNamespace(use_langgraph_eval=flag)


def test_flag_on_routes_to_graph(
    db_engine: Any, investigada_offer: int, patched_run: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the flag on, the evaluate stage calls the graph path, not v1."""
    monkeypatch.setattr(orch_module, "get_settings", _settings(True))
    only_eval = frozenset({"scrape", "filter", "research", "write"})
    orch = Orchestrator(skip_stages=only_eval)

    with patch.object(
        Orchestrator, "_eval_draft_graph", new_callable=AsyncMock, return_value=(1, 1, 0)
    ) as mock_graph:
        result = orch_module.asyncio.run(orch.run_for_user("jorge"))

    mock_graph.assert_awaited_once()
    assert result.drafts_generados == 1


def test_flag_off_uses_v1_path(
    db_engine: Any, investigada_offer: int, patched_run: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the flag off, the graph path is never called; v1 evaluator runs."""
    monkeypatch.setattr(orch_module, "get_settings", _settings(False))
    only_eval = frozenset({"scrape", "filter", "research", "write"})
    orch = Orchestrator(skip_stages=only_eval)

    with (
        patch.object(Orchestrator, "_eval_draft_graph", new_callable=AsyncMock) as mock_graph,
        patch(
            "src.agents.viability_evaluator.ViabilityEvaluator.evaluate", new_callable=AsyncMock
        ) as mock_eval,
    ):
        asyncio.run(orch.run_for_user("jorge"))

    mock_graph.assert_not_called()
    mock_eval.assert_awaited()
