"""Langfuse tracing for the ``evaluate_and_draft`` subgraph.

Best-practice instrumentation per the Langfuse skill:

* **LLM calls** are traced automatically by the ``langfuse.openai`` drop-in used
  in ``AzureOpenAIClient`` -- each completion becomes a generation with model,
  token usage and cost. That is the OpenAI integration, **not** LangChain
  (constitution D-02), so prompt caching and structured outputs are untouched.
* **Graph structure** is added on top: each node is a span (``instrument_node``)
  and a whole application run is one trace named by ``thread_id`` (``trace_run``),
  carrying ``session_id``/``user_id``/tags so generations group correctly.
* **PII is masked at the source**: the Langfuse client is created with a ``mask``
  that runs the v1 ``_mask_pii`` over every traced value, so the CV's email/phone
  in prompts never reaches Langfuse.

Tracing is a **silent no-op when the Langfuse keys are absent**: ``instrument_node``
returns the node unchanged, ``trace_run`` is a null context, and the
``langfuse.openai`` client degrades to a plain Azure OpenAI client.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import ExitStack, asynccontextmanager
from typing import Any, TypeVar, cast

import structlog

from src.logging_setup import _mask_pii

logger = structlog.get_logger(__name__)

NodeCoro = Callable[[Any], Awaitable[dict[str, object]]]
F = TypeVar("F", bound=NodeCoro)

_REQUIRED_KEYS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
_TRACE_TAGS = ["phase-10.5", "evaluate_and_draft"]

_initialized = False


def langfuse_enabled() -> bool:
    """Return ``True`` when both Langfuse keys are present in the environment."""
    return all(os.environ.get(key) for key in _REQUIRED_KEYS)


def _mask_data(data: Any) -> Any:
    """Langfuse mask: recursively run the v1 PII masking over traced values."""
    if isinstance(data, str):
        return _mask_pii(data)
    if isinstance(data, dict):
        return {k: _mask_data(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_mask_data(v) for v in data]
    return data


def init_langfuse() -> None:
    """Create the masked Langfuse singleton once, before any LLM call.

    Must run before the first ``langfuse.openai`` completion so that the
    integration reuses this masked client. No-op when tracing is disabled or
    already initialized.
    """
    global _initialized
    if _initialized or not langfuse_enabled():
        return
    from langfuse import Langfuse

    # mask is structurally a MaskFunction; langfuse's nominal type trips mypy.
    Langfuse(mask=_mask_data)  # type: ignore[arg-type]
    _initialized = True
    logger.info("langfuse_initialized")


def _get_client() -> Any | None:
    """Return the masked Langfuse client, or ``None`` when tracing is disabled."""
    if not langfuse_enabled():
        return None
    init_langfuse()
    from langfuse import get_client

    return get_client()


def instrument_node(name: str, fn: F) -> F:
    """Wrap a node coroutine in a Langfuse span, or return it unchanged.

    When tracing is disabled this returns *fn* itself (no wrapper, no overhead).
    LLM generations made inside the node auto-nest under this span. Tracing
    failures never propagate -- the node result is always returned.

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
        from langgraph.errors import GraphInterrupt

        try:
            with client.start_as_current_observation(name=name):
                out = await fn(state)
                client.update_current_span(output={"keys": sorted(out)})
                return out
        except GraphInterrupt:
            # interrupt() raises this to PAUSE the graph -- a control-flow signal,
            # not an error. Let it propagate; never swallow or re-run the node.
            raise
        except Exception as exc:  # tracing must never break the graph
            logger.warning("langfuse_span_failed", node=name, error=str(exc))
            return await fn(state)

    return cast(F, wrapped)


@asynccontextmanager
async def trace_run(
    thread_id: str, *, username: str, offer_id: int, session_id: str | None = None
) -> AsyncIterator[None]:
    """Open one Langfuse trace for an application run, or a null context.

    Sets ``user_id`` (the username) and a ``session_id`` so nested node spans and
    LLM generations group into one filterable trace, and traces sharing a
    ``session_id`` group into one Langfuse session.

    Args:
        thread_id: Stable id naming the trace (e.g. ``f"{run}:{offer_id}:{user}"``).
        username: Profile username (not PII; used as ``user_id``).
        offer_id: Offer DB id.
        session_id: Session to group this trace under. Defaults to ``thread_id``
            (one session per trace); pass a run-level id to group every offer of a
            run into a single session.

    Yields:
        Nothing; the body runs inside the trace when tracing is enabled.
    """
    client = _get_client()
    if client is None:
        yield
        return

    from langfuse import propagate_attributes

    try:
        with ExitStack() as stack:
            stack.enter_context(client.start_as_current_observation(name=thread_id))
            stack.enter_context(
                propagate_attributes(
                    trace_name=thread_id,
                    session_id=session_id or thread_id,
                    user_id=username,
                    tags=_TRACE_TAGS,
                    metadata={"offer_id": str(offer_id)},
                )
            )
            yield
    finally:
        try:
            client.flush()
        except Exception as exc:
            logger.warning("langfuse_flush_failed", error=str(exc))


def mask(text: str) -> str:
    """Mask emails/phones in *text* before it enters a trace (reuses v1 masking)."""
    return _mask_pii(text)
