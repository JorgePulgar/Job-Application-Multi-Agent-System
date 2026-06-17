"""Confidence router: the conditional edge that makes this a graph, not a chain.

Pure function of state -- no I/O, no LLM -- so it is trivially unit-testable and
cannot loop forever (the ``loop_count`` cap is enforced here).
"""

from __future__ import annotations

from src.graph.state import EvaluateDraftState

# Firm cap on confidence-loop passes. Lowered 2 -> 1 in Phase 10.6 Task 09: the
# cost baseline (COST-BASELINE.md) showed 8/9 offers maxed the loop while it was
# the dominant cost driver, so a single extra-research pass is allowed, not two.
MAX_LOOPS = 1

# Route targets returned to ``add_conditional_edges`` in build.py.
ROUTE_END = "end"
ROUTE_GATHER_MORE = "gather_more"
ROUTE_HUMAN_REVIEW = "human_review"
ROUTE_DRAFT = "draft"


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


def route_after_review(state: EvaluateDraftState) -> str:
    """Decide where to go after ``human_review``.

    Args:
        state: Graph state carrying ``human_decision``.

    Returns:
        ``"draft"`` when the reviewer's decision is apply/maybe, ``"end"`` when
        the reviewer overrode to skip (no draft).
    """
    decision = state["human_decision"]
    if decision is not None and decision.decision in ("apply", "maybe"):
        return ROUTE_DRAFT
    return ROUTE_END
