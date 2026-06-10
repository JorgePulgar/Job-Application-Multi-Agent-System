"""Confidence router: the conditional edge that makes this a graph, not a chain.

Pure function of state -- no I/O, no LLM -- so it is trivially unit-testable and
cannot loop forever (the ``loop_count`` cap is enforced here).
"""

from __future__ import annotations

from src.graph.state import EvaluateDraftState

# Firm cap on confidence-loop passes (mirrors the v1 max-2-regen rule).
MAX_LOOPS = 2

# Route targets returned to ``add_conditional_edges`` in build.py.
ROUTE_END = "end"
ROUTE_GATHER_MORE = "gather_more"
ROUTE_HUMAN_REVIEW = "human_review"


def route_on_confidence(state: EvaluateDraftState) -> str:
    """Decide where to go after ``assess_fit``.

    Args:
        state: Graph state carrying ``fit`` and (optionally) ``loop_count``.

    Returns:
        ``"end"`` when the verdict is SKIP (skip-is-short: no draft),
        ``"gather_more"`` when there is missing info and the loop cap is not yet
        reached, otherwise ``"human_review"``.
    """
    fit = state["fit"]
    if fit.recommendation == "skip":
        return ROUTE_END
    if fit.missing_info and state.get("loop_count", 0) < MAX_LOOPS:
        return ROUTE_GATHER_MORE
    return ROUTE_HUMAN_REVIEW
