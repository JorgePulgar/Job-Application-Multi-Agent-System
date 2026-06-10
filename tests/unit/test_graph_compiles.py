"""Smoke test: the evaluate_and_draft scaffold compiles and introspects.

No LLM calls -- nodes are placeholders. Verifies the README §3 topology is wired
and the graph can be drawn (``.get_graph()``).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from langgraph.checkpoint.memory import MemorySaver

from src.graph.build import (
    ASSESS_FIT,
    DRAFT_COVER_LETTER,
    EXTRACT_SPONSORSHIP,
    GATHER_MORE,
    HUMAN_REVIEW,
    INGEST_OFFER,
    MATCH_PROFILE,
    RESEARCH_COMPANY,
    build_graph,
)

# Compile-only: node factories capture the client but it is never called here.
_client = MagicMock()


def test_build_graph_compiles_and_exposes_nodes() -> None:
    """build_graph returns a compiled graph exposing every wired node."""
    compiled = build_graph(MemorySaver(), client=_client)

    drawable = compiled.get_graph()
    node_ids = set(drawable.nodes)

    expected = {
        INGEST_OFFER,
        RESEARCH_COMPANY,
        EXTRACT_SPONSORSHIP,
        MATCH_PROFILE,
        ASSESS_FIT,
        GATHER_MORE,
        HUMAN_REVIEW,
        DRAFT_COVER_LETTER,
    }
    assert expected <= node_ids


def test_build_graph_has_fanout_and_fanin_edges() -> None:
    """The three research branches fan out from ingest and fan in to assess_fit."""
    compiled = build_graph(MemorySaver(), client=_client)
    edges = {(e.source, e.target) for e in compiled.get_graph().edges}

    for branch in (RESEARCH_COMPANY, EXTRACT_SPONSORSHIP, MATCH_PROFILE):
        assert (INGEST_OFFER, branch) in edges
        assert (branch, ASSESS_FIT) in edges
