"""``draft_cover_letter`` node: tailored draft on an approved APPLY/MAYBE.

Generates a proof-first ``CoverLetterDraft`` with ``gpt-4o`` in the offer's
language, then runs the reused v1 prohibited-words + specificity post-check
(language-aware). Up to two regenerations with corrective feedback; if it still
fails, no generic draft is shipped -- state is flagged ``needs_manual_context``.
The draft body never discloses AI assistance (prompt + post-check).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from src.exceptions import JobAgentError
from src.graph.state import EvaluateDraftState
from src.models.company import CompanyDossier
from src.models.fit import CoverLetterDraft, FitAssessment, HumanDecision, ParsedOffer
from src.services import draft_lint, prompt_loader
from src.services.azure_openai import AzureOpenAIClient
from src.services.profiles import load_profile

logger = structlog.get_logger(__name__)

DraftNode = Callable[[EvaluateDraftState], Awaitable[dict[str, object]]]

_PROMPT = "graph_draft"
_MAX_RETRIES = 2
_IDIOMA_NOMBRE = {"es": "español", "en": "inglés"}


class DraftError(JobAgentError):
    """Raised when the draft node gets an invalid LLM response."""


def make_draft_cover_letter(client: AzureOpenAIClient) -> DraftNode:
    """Build the ``draft_cover_letter`` node bound to its LLM client.

    Args:
        client: Azure OpenAI client used for the gpt-4o call.

    Returns:
        The ``draft_cover_letter`` coroutine LangGraph invokes.
    """

    async def draft_cover_letter(state: EvaluateDraftState) -> dict[str, object]:
        """Generate and lint a tailored draft, or flag for manual context.

        Args:
            state: Graph state carrying ``parsed``, ``dossier``, ``fit`` and
                (optionally) ``human_decision``.

        Returns:
            ``{"draft": CoverLetterDraft, "needs_manual_context": False}`` on a
            clean draft, or ``{"draft": None, "needs_manual_context": True}`` if
            the post-check still fails after the regen cap.
        """
        parsed: ParsedOffer = state["parsed"]
        dossier: CompanyDossier = state["dossier"]
        fit: FitAssessment = state["fit"]
        decision: HumanDecision | None = state.get("human_decision")
        profile = load_profile(state["username"])

        hook = fit.tailoring.cover_letter_hook if fit.tailoring is not None else ""
        lead_angle = _lead_angle(decision, hook)
        cv_emphasis = fit.tailoring.cv_emphasis if fit.tailoring is not None else []

        system = prompt_loader.load_system(_PROMPT, cv=profile.cv_for_prompt())
        base_user = prompt_loader.load_user(
            _PROMPT,
            titulo=parsed.title,
            empresa=parsed.company,
            dossier=dossier.to_summary_for_prompt(),
            hook=hook or "(sin gancho específico; usa un dato del dossier)",
            lead_angle=lead_angle or "(libre)",
            cv_emphasis=_bullets(cv_emphasis),
            idioma=_IDIOMA_NOMBRE[parsed.detected_language],
        )

        last_issues: list[str] = []
        log = logger.bind(offer_id=state.get("offer_id"), language=parsed.detected_language)

        for attempt in range(_MAX_RETRIES + 1):
            user = base_user if attempt == 0 else f"{base_user}\n\n{_feedback(last_issues)}"
            result = await client.chat(
                deployment="4o",
                system=system,
                user=user,
                response_format=CoverLetterDraft,
                cacheable_system=True,
            )
            if result.parsed is None or not isinstance(result.parsed, CoverLetterDraft):
                raise DraftError("LLM did not return a valid CoverLetterDraft")

            draft: CoverLetterDraft = result.parsed
            lint = draft_lint.lint_cover_letter(
                draft,
                dossier=dossier,
                empresa=parsed.company,
                language=parsed.detected_language,
            )
            if lint.ok:
                log.info("graph_draft_done", attempt=attempt)
                return {"draft": draft, "needs_manual_context": False}

            last_issues = lint.issues
            log.info("graph_draft_lint_failed", attempt=attempt, issues=last_issues)

        log.warning("graph_draft_flagged_after_retries", issues=last_issues)
        return {"draft": None, "needs_manual_context": True}

    return draft_cover_letter


def _lead_angle(decision: HumanDecision | None, hook: str) -> str:
    """Pick the lead angle: reviewer override wins, else the tailoring hook."""
    if decision is not None and decision.lead_angle:
        return decision.lead_angle
    return hook


def _feedback(issues: list[str]) -> str:
    """Render lint issues as a corrective instruction block for regeneration."""
    bullets = "\n".join(f"- {issue}" for issue in issues)
    return (
        "## Corrige estos problemas del borrador anterior\n"
        "El borrador anterior fue rechazado por estos motivos. Corrígelos todos:\n"
        f"{bullets}"
    )


def _bullets(items: list[str]) -> str:
    """Render a list as a markdown bullet block, or a dash when empty."""
    return "\n".join(f"- {item}" for item in items) if items else "- (ninguno)"
