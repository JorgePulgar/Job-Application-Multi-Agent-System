"""``match_profile`` fan-out branch: requirement-by-requirement profile match.

Uses ``gpt-4o-mini`` to map each required/preferred skill to met/partial/missing
against the user's YAML profile (NOT Claude memory), and to surface
``standout_points`` and ``gaps``. Phase 10.6 Task 09 moved this node from
``gpt-4o`` to ``gpt-4o-mini``: the cost baseline (COST-BASELINE.md) showed it was
16% of graph cost while doing mechanical requirement-by-requirement matching, and
the eval set guards that the verdict it feeds does not regress.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from src.exceptions import JobAgentError
from src.graph.state import EvaluateDraftState
from src.models.fit import ParsedOffer, RequirementMatch
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient
from src.services.profiles import load_profile

logger = structlog.get_logger(__name__)

MatchProfileNode = Callable[[EvaluateDraftState], Awaitable[dict[str, RequirementMatch]]]

_PROMPT = "graph_match"
_IDIOMA_NOMBRE = {"es": "español", "en": "inglés"}


class MatchProfileError(JobAgentError):
    """Raised when the requirement match cannot be produced."""


def make_match_profile(client: AzureOpenAIClient) -> MatchProfileNode:
    """Build the ``match_profile`` node bound to its LLM client.

    The user profile is loaded per-call from ``config/users/{username}.yaml`` via
    the existing loader.

    Args:
        client: Azure OpenAI client used for the gpt-4o-mini call.

    Returns:
        The ``match_profile`` coroutine LangGraph invokes.
    """

    async def match_profile(state: EvaluateDraftState) -> dict[str, RequirementMatch]:
        """Map the offer's requirements against the user's profile.

        Args:
            state: Graph state carrying ``parsed`` and ``username``.

        Returns:
            ``{"requirements": RequirementMatch}``.

        Raises:
            MatchProfileError: If the LLM returns an invalid match.
        """
        parsed: ParsedOffer = state["parsed"]
        profile = load_profile(state["username"])

        system = prompt_loader.load_system(_PROMPT, cv=profile.cv_for_prompt())
        user = prompt_loader.load_user(
            _PROMPT,
            titulo=parsed.title,
            empresa=parsed.company,
            seniority=parsed.seniority or "No especificada",
            required_skills=_bullets(parsed.required_skills),
            preferred_skills=_bullets(parsed.preferred_skills),
            idioma=_IDIOMA_NOMBRE[parsed.detected_language],
        )

        result = await client.chat(
            deployment="mini",
            system=system,
            user=user,
            response_format=RequirementMatch,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, RequirementMatch):
            raise MatchProfileError("LLM did not return a valid RequirementMatch")

        match: RequirementMatch = result.parsed
        logger.info(
            "graph_match_profile_done",
            username=state["username"],
            items=len(match.items),
            gaps=len(match.gaps),
        )
        return {"requirements": match}

    return match_profile


def _bullets(items: list[str]) -> str:
    """Render skills as a markdown bullet list, or a dash when empty."""
    return "\n".join(f"- {item}" for item in items) if items else "- (ninguno)"
