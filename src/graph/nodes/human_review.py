"""``human_review`` node: human-in-the-loop via LangGraph ``interrupt()``.

Presents the ``FitAssessment`` (verdict, score, red flags, gaps) plus up to three
clarifying questions -- only the open ``missing_info`` items, i.e. the unknowns
that would actually change the verdict or tailoring. The graph pauses here; on
resume the dashboard payload is validated into a ``HumanDecision`` and written to
state. Because the pause is checkpointed, a paused application survives a process
restart and resumes on the same ``thread_id``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from langgraph.types import interrupt

from src.graph.state import EvaluateDraftState
from src.models.fit import FitAssessment, HumanDecision, RequirementMatch

logger = structlog.get_logger(__name__)

HumanReviewNode = Callable[[EvaluateDraftState], Awaitable[dict[str, object]]]

_MAX_QUESTIONS = 3


def make_human_review() -> HumanReviewNode:
    """Build the ``human_review`` node.

    Takes no dependencies -- it pauses the graph and consumes the resume payload.

    Returns:
        The ``human_review`` coroutine LangGraph invokes.
    """

    async def human_review(state: EvaluateDraftState) -> dict[str, object]:
        """Pause for human review and capture the reviewer's decision.

        Args:
            state: Graph state carrying ``fit`` and (optionally) ``requirements``.

        Returns:
            ``{"human_decision": HumanDecision}`` once resumed.
        """
        fit: FitAssessment = state["fit"]
        requirements: RequirementMatch | None = state.get("requirements")

        payload: dict[str, Any] = {
            "verdict": fit.recommendation,
            "fit_level": fit.fit_level,
            "score": fit.score,
            "reasoning": fit.reasoning,
            "red_flags": fit.red_flags,
            "gaps": requirements.gaps if requirements is not None else [],
            # Only the open unknowns; these are what would move the verdict.
            "questions": fit.missing_info[:_MAX_QUESTIONS],
        }

        raw = interrupt(payload)
        decision = HumanDecision.model_validate(raw)
        logger.info("graph_human_review_done", decision=decision.decision)
        return {"human_decision": decision}

    return human_review
