"""Assembly of the ``evaluate_and_draft`` subgraph.

Wires the real nodes (ingest -> research fan-out -> assess_fit -> confidence
routing -> human_review -> draft) with the README §3 topology. ``human_review``
(Task 07) and ``draft_cover_letter`` (Task 08) are still placeholders returning
``{}``; everything up to and including the confidence loop is live.

Node dependencies are injected here and captured by the node factory closures, so
nodes stay pure ``(state)`` callables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.db.base import get_session
from src.graph.nodes.assess_fit import make_assess_fit
from src.graph.nodes.gather_more import make_gather_more
from src.graph.nodes.human_review import make_human_review
from src.graph.nodes.ingest import SessionFactory, make_ingest_offer
from src.graph.nodes.match_profile import make_match_profile
from src.graph.nodes.research_company import make_research_company
from src.graph.nodes.route import (
    ROUTE_DRAFT,
    ROUTE_END,
    ROUTE_GATHER_MORE,
    ROUTE_HUMAN_REVIEW,
    route_after_review,
    route_on_confidence,
)
from src.graph.nodes.sponsorship import make_extract_sponsorship
from src.graph.state import EvaluateDraftState
from src.services.azure_openai import AzureOpenAIClient

# Dedicated checkpointer DB, kept separate from the app's state.db so langgraph's
# internal checkpoint tables never collide with the application schema.
CHECKPOINT_DB_PATH = Path("data") / "graph_checkpoints.db"

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


def _draft_cover_letter(state: EvaluateDraftState) -> dict[str, object]:
    """Placeholder for the draft node (Task 08)."""
    return {}


def open_checkpointer(path: Path = CHECKPOINT_DB_PATH) -> Any:
    """Return an async context manager yielding an ``AsyncSqliteSaver``.

    The caller enters it and passes the saver to :func:`build_graph`; the same
    DB file across invocations makes a paused application resumable after a
    process restart.

    Args:
        path: Checkpointer SQLite file. Defaults to ``data/graph_checkpoints.db``.

    Returns:
        Async context manager yielding the checkpointer.
    """
    return AsyncSqliteSaver.from_conn_string(str(path))


def thread_config(username: str, offer_id: int) -> dict[str, Any]:
    """Build the per-application LangGraph config (stable ``thread_id``).

    Args:
        username: Profile username.
        offer_id: Offer DB id.

    Returns:
        Config dict with ``thread_id = f"{username}:{offer_id}"`` so a re-invoked
        run resumes the same paused application instead of starting over.
    """
    return {"configurable": {"thread_id": f"{username}:{offer_id}"}}


def build_graph(
    checkpointer: BaseCheckpointSaver[Any],
    *,
    client: AzureOpenAIClient,
    session_factory: SessionFactory = get_session,
) -> CompiledEvalGraph:
    """Build and compile the ``evaluate_and_draft`` subgraph.

    Args:
        checkpointer: Persistence backend for graph state. ``MemorySaver`` in
            tests; an async SqliteSaver in production (wired in Task 07).
        client: Azure OpenAI client injected into every LLM node.
        session_factory: Callable yielding a context-managed ``Session`` for the
            DB-touching nodes. Defaults to the app session factory.

    Returns:
        The compiled graph. ``human_review`` and ``draft_cover_letter`` are
        placeholders until Tasks 07-08.
    """
    graph: StateGraph[Any, Any, Any, Any] = StateGraph(EvaluateDraftState)

    # langgraph's add_node overloads do not cleanly accept our precise async node
    # signatures; register through an Any-typed map to keep it one place.
    nodes: dict[str, Any] = {
        INGEST_OFFER: make_ingest_offer(client, session_factory),
        RESEARCH_COMPANY: make_research_company(client, session_factory),
        EXTRACT_SPONSORSHIP: make_extract_sponsorship(client),
        MATCH_PROFILE: make_match_profile(client),
        ASSESS_FIT: make_assess_fit(client),
        GATHER_MORE: make_gather_more(),
        HUMAN_REVIEW: make_human_review(),
        DRAFT_COVER_LETTER: _draft_cover_letter,
    }
    for name, action in nodes.items():
        graph.add_node(name, action)

    graph.add_edge(START, INGEST_OFFER)

    # Fan-out: ingest -> three parallel research branches.
    graph.add_edge(INGEST_OFFER, RESEARCH_COMPANY)
    graph.add_edge(INGEST_OFFER, EXTRACT_SPONSORSHIP)
    graph.add_edge(INGEST_OFFER, MATCH_PROFILE)

    # Fan-in: all three branches -> assess_fit (runs after all complete).
    graph.add_edge(RESEARCH_COMPANY, ASSESS_FIT)
    graph.add_edge(EXTRACT_SPONSORSHIP, ASSESS_FIT)
    graph.add_edge(MATCH_PROFILE, ASSESS_FIT)

    # Confidence routing: SKIP ends short, missing-info loops back (cap 2),
    # confident proceeds to human review.
    graph.add_conditional_edges(
        ASSESS_FIT,
        route_on_confidence,
        {
            ROUTE_END: END,
            ROUTE_GATHER_MORE: GATHER_MORE,
            ROUTE_HUMAN_REVIEW: HUMAN_REVIEW,
        },
    )
    graph.add_edge(GATHER_MORE, ASSESS_FIT)

    # After human review: draft on apply/maybe, end on a skip override.
    graph.add_conditional_edges(
        HUMAN_REVIEW,
        route_after_review,
        {
            ROUTE_DRAFT: DRAFT_COVER_LETTER,
            ROUTE_END: END,
        },
    )
    graph.add_edge(DRAFT_COVER_LETTER, END)

    return graph.compile(checkpointer=checkpointer)
