"""Integration test: interrupt + SqliteSaver durability + resume.

Builds the real review tail (``human_review`` + ``route_after_review``) compiled
with a real ``AsyncSqliteSaver``. Runs until the ``interrupt()``, drops the
in-memory graph, rebuilds a fresh graph from a fresh saver on the *same* DB file,
and resumes -- proving a paused application survives a process restart and that a
``skip`` override ends without drafting. The full pipeline wiring is covered by
the compile smoke test; this isolates the HITL/checkpointer mechanics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.graph.build import open_checkpointer, thread_config
from src.graph.nodes.human_review import make_human_review
from src.graph.nodes.route import ROUTE_DRAFT, ROUTE_END, route_after_review
from src.graph.state import EvaluateDraftState
from src.models.fit import CoverLetterDraft, FitAssessment

HUMAN_REVIEW = "human_review"
DRAFT = "draft"


def _build_tail(checkpointer: Any) -> Any:
    """Compile the review tail: human_review -> (draft | end)."""
    graph: StateGraph[Any, Any, Any, Any] = StateGraph(EvaluateDraftState)

    async def _draft_stub(state: EvaluateDraftState) -> dict[str, object]:
        return {"draft": CoverLetterDraft(subject="s", body="b", lead_angle="a", hook="h")}

    graph.add_node(HUMAN_REVIEW, make_human_review())
    graph.add_node(DRAFT, _draft_stub)
    graph.add_edge(START, HUMAN_REVIEW)
    graph.add_conditional_edges(
        HUMAN_REVIEW,
        route_after_review,
        {ROUTE_DRAFT: DRAFT, ROUTE_END: END},
    )
    graph.add_edge(DRAFT, END)
    return graph.compile(checkpointer=checkpointer)


def _fit() -> FitAssessment:
    return FitAssessment(
        fit_level="moderate",
        recommendation="maybe",
        score=60,
        reasoning="Encaje con dudas.",
        red_flags=[],
        missing_info=["¿Rango salarial?", "¿Modalidad exacta?"],
        tailoring=None,
    )


def _initial() -> dict[str, Any]:
    return {"offer_id": 1, "username": "jorge", "fit": _fit()}


@pytest.mark.asyncio
async def test_interrupt_persists_and_resumes_to_draft(tmp_path: Path) -> None:
    """Run to interrupt, rebuild from the same DB, resume apply -> reaches draft."""
    db = tmp_path / "cp.db"
    cfg = thread_config("jorge", 1)

    # --- First process: run until interrupt, then drop the graph. ---
    async with open_checkpointer(db) as saver:
        graph = _build_tail(saver)
        result = await graph.ainvoke(_initial(), config=cfg)

        assert "__interrupt__" in result
        payload = result["__interrupt__"][0].value
        assert payload["verdict"] == "maybe"
        assert len(payload["questions"]) == 2

    # --- Second process: fresh saver + fresh graph on the SAME db file. ---
    async with open_checkpointer(db) as saver2:
        graph2 = _build_tail(saver2)

        snapshot = await graph2.aget_state(cfg)
        assert snapshot.next  # still paused at an unfinished node

        out = await graph2.ainvoke(
            Command(resume={"decision": "apply", "lead_angle": None, "clarifications": {}}),
            config=cfg,
        )

    assert out["human_decision"].decision == "apply"
    assert out["draft"] is not None


@pytest.mark.asyncio
async def test_skip_override_ends_without_draft(tmp_path: Path) -> None:
    """A skip override after review ends the graph with no draft."""
    db = tmp_path / "cp.db"
    cfg = thread_config("jorge", 2)

    async with open_checkpointer(db) as saver:
        graph = _build_tail(saver)
        await graph.ainvoke(_initial(), config=cfg)
        out = await graph.ainvoke(
            Command(resume={"decision": "skip", "lead_angle": None, "clarifications": {}}),
            config=cfg,
        )

    assert out["human_decision"].decision == "skip"
    assert out.get("draft") is None
