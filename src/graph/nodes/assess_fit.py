"""``assess_fit`` fan-in node: merge the three branches into a ``FitAssessment``.

Reads ``parsed`` + the three branch outputs (``dossier``, ``sponsorship``,
``requirements``) and produces a single honest verdict with ``gpt-4o``, encoding
the skill's decision rubric (hard SKIP blockers only; soft gaps never a SKIP
alone; unknowns to ``missing_info``; ``tailoring`` only when apply/maybe).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from src.exceptions import JobAgentError
from src.graph.state import EvaluateDraftState
from src.models.company import CompanyDossier
from src.models.fit import FitAssessment, ParsedOffer, RequirementMatch, SponsorshipSignal
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)

AssessFitNode = Callable[[EvaluateDraftState], Awaitable[dict[str, FitAssessment]]]

_PROMPT = "graph_assess_fit"
_IDIOMA_NOMBRE = {"es": "español", "en": "inglés"}


class AssessFitError(JobAgentError):
    """Raised when the fit assessment cannot be produced."""


def make_assess_fit(client: AzureOpenAIClient) -> AssessFitNode:
    """Build the ``assess_fit`` node bound to its LLM client.

    Args:
        client: Azure OpenAI client used for the gpt-4o call.

    Returns:
        The ``assess_fit`` coroutine LangGraph invokes.
    """

    async def assess_fit(state: EvaluateDraftState) -> dict[str, FitAssessment]:
        """Produce the final ``FitAssessment`` from the merged branches.

        Args:
            state: Graph state carrying ``parsed``, ``dossier``, ``sponsorship``,
                ``requirements``.

        Returns:
            ``{"fit": FitAssessment}``.

        Raises:
            AssessFitError: If the LLM returns an invalid assessment.
        """
        parsed: ParsedOffer = state["parsed"]
        dossier: CompanyDossier = state["dossier"]
        sponsorship: SponsorshipSignal = state["sponsorship"]
        requirements: RequirementMatch = state["requirements"]

        system = prompt_loader.load_system(_PROMPT)
        user = prompt_loader.load_user(
            _PROMPT,
            titulo=parsed.title,
            empresa=parsed.company,
            seniority=parsed.seniority or "No especificada",
            dossier=dossier.to_summary_for_prompt(),
            sponsorship=_sponsorship_summary(sponsorship),
            requirements=_requirements_summary(requirements),
            idioma=_IDIOMA_NOMBRE[parsed.detected_language],
        )

        result = await client.chat(
            deployment="4o",
            system=system,
            user=user,
            response_format=FitAssessment,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, FitAssessment):
            raise AssessFitError("LLM did not return a valid FitAssessment")

        fit: FitAssessment = result.parsed
        logger.info(
            "graph_assess_fit_done",
            recommendation=fit.recommendation,
            fit_level=fit.fit_level,
            score=fit.score,
        )
        return {"fit": fit}

    return assess_fit


def _sponsorship_summary(s: SponsorshipSignal) -> str:
    """Render the sponsorship signal as compact prompt text."""
    return (
        f"- needs_sponsorship: {s.needs_sponsorship}\n"
        f"- sponsorship_offered: {s.sponsorship_offered}\n"
        f"- geo_viable_for_spain: {s.geo_viable_for_spain}\n"
        f"- working_language: {s.working_language or 'desconocido'}\n"
        f"- blocker: {s.blocker or 'ninguno'}"
    )


def _requirements_summary(r: RequirementMatch) -> str:
    """Render the requirement match as compact prompt text."""
    items = "\n".join(f"- [{i.status}] {i.requirement}: {i.note}" for i in r.items) or "- (ninguno)"
    standout = ", ".join(r.standout_points) or "ninguno"
    gaps = ", ".join(r.gaps) or "ninguno"
    return f"Requisitos:\n{items}\nDestaca en: {standout}\nCarencias: {gaps}"
