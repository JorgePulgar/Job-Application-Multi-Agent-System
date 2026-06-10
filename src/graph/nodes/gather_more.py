"""``gather_more`` node: targeted extra research for the confidence loop.

Runs when ``assess_fit`` left ``missing_info`` unresolved and the loop cap is not
yet hit. Does focused ``search_web`` lookups per missing-info item, folds the
findings into the dossier notes so the next ``assess_fit`` can use them, and
increments ``loop_count``. Routes back to ``assess_fit`` (edge wired in build.py).
The loop cap lives in ``route_on_confidence`` so this node can never spin.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from src.graph.state import EvaluateDraftState
from src.models.company import CompanyDossier
from src.models.fit import FitAssessment, ParsedOffer
from src.models.search import SearchResult
from src.services.web_search import search_web

logger = structlog.get_logger(__name__)

GatherMoreNode = Callable[[EvaluateDraftState], Awaitable[dict[str, object]]]

_RESULTS_PER_ITEM = 2


def make_gather_more() -> GatherMoreNode:
    """Build the ``gather_more`` node.

    Takes no dependencies -- it reuses the module-level ``search_web`` service.

    Returns:
        The ``gather_more`` coroutine LangGraph invokes.
    """

    async def gather_more(state: EvaluateDraftState) -> dict[str, object]:
        """Research the open ``missing_info`` items and fold them into the dossier.

        Args:
            state: Graph state carrying ``parsed``, ``dossier``, ``fit`` and
                (optionally) ``loop_count``.

        Returns:
            ``{"dossier": <enriched>, "loop_count": <n+1>}``.
        """
        parsed: ParsedOffer = state["parsed"]
        dossier: CompanyDossier = state["dossier"]
        fit: FitAssessment = state["fit"]
        loop_count = state.get("loop_count", 0)

        findings: list[str] = []
        for item in fit.missing_info:
            results: list[SearchResult] = await search_web(
                f"{parsed.company} {item}", n=_RESULTS_PER_ITEM
            )
            for r in results:
                if r.snippet:
                    findings.append(f"[{item}] {r.snippet}")

        enriched = dossier.model_copy(update={"cultura_notas": [*dossier.cultura_notas, *findings]})
        logger.info(
            "graph_gather_more_done",
            loop_count=loop_count + 1,
            items=len(fit.missing_info),
            findings=len(findings),
        )
        return {"dossier": enriched, "loop_count": loop_count + 1}

    return gather_more
