"""Compile-only scaffold of the ``evaluate_and_draft`` subgraph (Task 01).

Wires placeholder nodes -- each returns ``{}`` -- with the README §3 topology so
the graph compiles and can be introspected via ``.get_graph()``. No LLM calls
yet. Real node bodies land in Tasks 03-08, confidence routing in Task 06, and the
``interrupt()`` + SqliteSaver checkpointer in Task 07.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.graph.state import EvaluateDraftState

# The langgraph generics carry four type params (state/context/input/output);
# the scaffold does not constrain them, so fix them to ``Any``.
CompiledEvalGraph = CompiledStateGraph[Any, Any, Any, Any]

# Node names, kept as constants so wiring and routing stay in sync.
INGEST_OFFER = "ingest_offer"
RESEARCH_COMPANY = "research_company"
EXTRACT_SPONSORSHIP = "extract_sponsorship"
MATCH_PROFILE = "match_profile"
ASSESS_FIT = "assess_fit"
GATHER_MORE = "gather_more"
HUMAN_REVIEW = "human_review"
DRAFT_COVER_LETTER = "draft_cover_letter"


def _ingest_offer(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the ingest node (Task 03)."""
    return {}


def _research_company(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the company-research fan-out branch (Task 04)."""
    return {}


def _extract_sponsorship(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the sponsorship-signal fan-out branch (Task 04)."""
    return {}


def _match_profile(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the profile-match fan-out branch (Task 04)."""
    return {}


def _assess_fit(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the fan-in assessment node (Task 05)."""
    return {}


def _gather_more(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the confidence-loop re-research node (Task 06)."""
    return {}


def _human_review(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the human-in-the-loop interrupt node (Task 07)."""
    return {}


def _draft_cover_letter(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the draft node (Task 08)."""
    return {}


def _route_on_confidence(state: EvaluateDraftState) -> str:
    """Placeholder confidence router (real logic in Task 06).

    Always routes to ``human_review`` for now so the compiled graph has a
    reachable draft path. Task 06 adds the ``skip`` (END) and ``gather_more``
    (loop, max 2) branches driven by ``fit`` + ``loop_count``.
    """
    return HUMAN_REVIEW


def build_graph(checkpointer: BaseCheckpointSaver[Any]) -> CompiledEvalGraph:
    """Build and compile the ``evaluate_and_draft`` subgraph.

    Args:
        checkpointer: Persistence backend for graph state. ``MemorySaver`` in
            tests; an async SqliteSaver in production (wired in Task 07).

    Returns:
        The compiled graph. Nodes are placeholders returning ``{}`` until
        Tasks 03-08 fill them in.
    """
    graph: StateGraph[Any, Any, Any, Any] = StateGraph(EvaluateDraftState)

    graph.add_node(INGEST_OFFER, _ingest_offer)
    graph.add_node(RESEARCH_COMPANY, _research_company)
    graph.add_node(EXTRACT_SPONSORSHIP, _extract_sponsorship)
    graph.add_node(MATCH_PROFILE, _match_profile)
    graph.add_node(ASSESS_FIT, _assess_fit)
    graph.add_node(GATHER_MORE, _gather_more)
    graph.add_node(HUMAN_REVIEW, _human_review)
    graph.add_node(DRAFT_COVER_LETTER, _draft_cover_letter)

    graph.add_edge(START, INGEST_OFFER)

    # Fan-out: ingest -> three parallel research branches.
    graph.add_edge(INGEST_OFFER, RESEARCH_COMPANY)
    graph.add_edge(INGEST_OFFER, EXTRACT_SPONSORSHIP)
    graph.add_edge(INGEST_OFFER, MATCH_PROFILE)

    # Fan-in: all three branches -> assess_fit (runs after all complete).
    graph.add_edge(RESEARCH_COMPANY, ASSESS_FIT)
    graph.add_edge(EXTRACT_SPONSORSHIP, ASSESS_FIT)
    graph.add_edge(MATCH_PROFILE, ASSESS_FIT)

    # Confidence routing: skip (END), loop (gather_more), or proceed to review.
    graph.add_conditional_edges(
        ASSESS_FIT,
        _route_on_confidence,
        {
            "skip": END,
            GATHER_MORE: GATHER_MORE,
            HUMAN_REVIEW: HUMAN_REVIEW,
        },
    )
    graph.add_edge(GATHER_MORE, ASSESS_FIT)

    graph.add_edge(HUMAN_REVIEW, DRAFT_COVER_LETTER)
    graph.add_edge(DRAFT_COVER_LETTER, END)

    return graph.compile(checkpointer=checkpointer)
