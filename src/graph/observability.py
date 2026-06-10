"""Langfuse tracing for the ``evaluate_and_draft`` subgraph.

Instruments the graph with the **Langfuse SDK directly** -- not the
``langfuse.langchain`` CallbackHandler, which requires LangChain-classic that this
project deliberately avoids (constitution D-02/D-06). Each node is wrapped in a
span; the whole application run is one trace named by ``thread_id``; per-application
token/cost is attached from the existing usage tracker (LLM calls go through the
``openai`` SDK, so token usage is summed by the v1 cost tracker and surfaced in run
logs, then mirrored onto the trace here).

Tracing is a **silent no-op when the Langfuse keys are absent**: ``instrument_node``
returns the node unchanged (zero overhead) and ``trace_run`` is a null context, so
the graph runs identically without Langfuse configured.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar, cast

import structlog

from src.logging_setup import _mask_pii

logger = structlog.get_logger(__name__)

NodeCoro = Callable[[Any], Awaitable[dict[str, object]]]
F = TypeVar("F", bound=NodeCoro)

_REQUIRED_KEYS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")

_client: Any | None = None


def langfuse_enabled() -> bool:
    """Return ``True`` when both Langfuse keys are present in the environment."""
    return all(os.environ.get(key) for key in _REQUIRED_KEYS)


def _get_client() -> Any | None:
    """Return a cached Langfuse client, or ``None`` when tracing is disabled."""
    global _client
    if not langfuse_enabled():
        return None
    if _client is None:
        from langfuse import get_client

        _client = get_client()
    return _client


def instrument_node(name: str, fn: F) -> F:
    """Wrap a node coroutine in a Langfuse span, or return it unchanged.

    When tracing is disabled this returns *fn* itself (no wrapper, no overhead).
    Tracing failures never propagate -- the node result is always returned.

    Args:
        name: Span name (the node name).
        fn: The node coroutine to wrap.

    Returns:
        The wrapped coroutine, or *fn* unchanged when tracing is disabled.
    """
    if not langfuse_enabled():
        return fn

    async def wrapped(state: Any) -> dict[str, object]:
        client = _get_client()
        if client is None:
            return await fn(state)
        try:
            with client.start_as_current_observation(name=name):
                out = await fn(state)
                client.update_current_span(output={"keys": sorted(out)})
                return out
        except Exception as exc:  # tracing must never break the graph
            logger.warning("langfuse_span_failed", node=name, error=str(exc))
            return await fn(state)

    return cast(F, wrapped)


@asynccontextmanager
async def trace_run(thread_id: str, *, username: str, offer_id: int) -> AsyncIterator[None]:
    """Open one Langfuse trace for an application run, or a null context.

    Args:
        thread_id: Stable id naming the trace (``f"{username}:{offer_id}"``).
        username: Profile username (not PII).
        offer_id: Offer DB id.

    Yields:
        Nothing; the body runs inside the trace when tracing is enabled.
    """
    client = _get_client()
    if client is None:
        yield
        return
    try:
        with client.start_as_current_observation(name=thread_id):
            client.update_current_span(
                metadata={"thread_id": thread_id, "username": username, "offer_id": offer_id}
            )
            yield
    finally:
        try:
            client.flush()
        except Exception as exc:
            logger.warning("langfuse_flush_failed", error=str(exc))


def record_application_cost(total_tokens: int, cost_usd: float) -> None:
    """Attach per-application token/cost to the current trace (no-op if disabled).

    Args:
        total_tokens: Summed token usage across the run's LLM calls.
        cost_usd: Estimated USD cost across the run.
    """
    client = _get_client()
    if client is None:
        return
    try:
        client.update_current_span(metadata={"total_tokens": total_tokens, "cost_usd": cost_usd})
    except Exception as exc:
        logger.warning("langfuse_cost_record_failed", error=str(exc))


def mask(text: str) -> str:
    """Mask emails/phones in *text* before it enters a trace (reuses v1 masking)."""
    return _mask_pii(text)
