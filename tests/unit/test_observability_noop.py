"""Observability is a silent no-op when Langfuse keys are absent."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.graph import observability
from src.graph.build import build_graph


@pytest.fixture()
def _no_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)


async def _node(state: Any) -> dict[str, object]:
    return {"ran": True}


def test_disabled_without_keys(_no_keys: None) -> None:
    assert observability.langfuse_enabled() is False


def test_instrument_node_is_passthrough_when_disabled(_no_keys: None) -> None:
    """With no keys, instrument_node returns the node unchanged (zero overhead)."""
    wrapped = observability.instrument_node("ingest", _node)
    assert wrapped is _node


@pytest.mark.asyncio
async def test_wrapped_node_runs_when_disabled(_no_keys: None) -> None:
    node = observability.instrument_node("ingest", _node)
    out = await node({"offer_id": 1})
    assert out == {"ran": True}


@pytest.mark.asyncio
async def test_trace_run_and_init_are_noops(_no_keys: None) -> None:
    """trace_run yields and init_langfuse is silent when disabled."""
    observability.init_langfuse()  # must not raise or initialize
    async with observability.trace_run("jorge:1", username="jorge", offer_id=1):
        pass


def test_instrument_node_wraps_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """With keys present, instrument_node returns a new wrapper (not the node)."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    wrapped = observability.instrument_node("ingest", _node)
    assert wrapped is not _node


def test_build_graph_compiles_without_keys(_no_keys: None) -> None:
    """The full graph still compiles (instrumented) with no Langfuse keys."""
    compiled = build_graph(MemorySaver(), client=MagicMock())
    assert "ingest_offer" in set(compiled.get_graph().nodes)
