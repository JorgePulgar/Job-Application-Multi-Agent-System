"""Scorers for the ``evaluate_and_draft`` eval harness (Phase 10.5, Task 10).

Three scores are produced per dataset item:

* **verdict_agreement** — exact match of the graph's recommendation against the
  reference label (apply/maybe/skip). Half credit for an apply<->maybe near-miss
  (both non-skip), zero when one side is ``skip`` and the other is not. Pure
  function, no I/O.
* **faithfulness** — LLM-as-judge (``gpt-4o``): does the analysis/draft invent
  facts about the company/offer not grounded in the offer + dossier? Returns a
  0-1 score (100 -> 1.0). Mockable via the injected ``AzureOpenAIClient``.
* **specificity** — reuses the v1 draft-lint specificity rule: the draft must name
  the company and cite at least one concrete dossier fact. 1.0 pass / 0.0 fail;
  ``None`` when no draft was produced (a ``skip`` verdict ships no draft).

The scorers are deliberately plain callables so the eval runner can record them to
Langfuse *or* dump them to ``data/evals/`` unchanged, and so they unit-test without
a network.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from pydantic import BaseModel, Field

from src.exceptions import JobAgentError
from src.models.company import CompanyDossier
from src.models.fit import CoverLetterDraft, Recommendation
from src.services import draft_lint, prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)

# Score names (kept stable so Langfuse score series line up across runs).
VERDICT_AGREEMENT = "verdict_agreement"
FAITHFULNESS = "faithfulness"
SPECIFICITY = "specificity"

_FAITHFULNESS_PROMPT = "eval_faithfulness"


class EvalError(JobAgentError):
    """Raised when an eval scorer gets an invalid LLM response."""


@dataclass
class ScoreResult:
    """A single named score with a 0-1 value and a short comment.

    Attributes:
        name: Score name (one of the module constants).
        value: Score in ``[0.0, 1.0]``.
        comment: One-line justification, safe to log/trace (no PII).
    """

    name: str
    value: float
    comment: str


class FaithfulnessVerdict(BaseModel):
    """Structured output of the faithfulness judge.

    Attributes:
        score: Grounding score 0-100 (100 = fully grounded in the sources).
        unsupported_claims: Claims about the company/offer not backed by sources.
        comment: One-sentence justification of the score.
    """

    score: int = Field(ge=0, le=100, description="Grounding score 0-100.")
    unsupported_claims: list[str]
    comment: str


def score_verdict_agreement(prediction: Recommendation, reference: Recommendation) -> ScoreResult:
    """Score the graph verdict against the reference label.

    Args:
        prediction: The graph's recommendation (apply/maybe/skip).
        reference: The reference recommendation from the dataset.

    Returns:
        ``ScoreResult`` with value 1.0 on exact match, 0.5 on an apply<->maybe
        near-miss (both non-skip), else 0.0.
    """
    if prediction == reference:
        return ScoreResult(VERDICT_AGREEMENT, 1.0, f"exact match ({reference})")
    if "skip" not in (prediction, reference):
        return ScoreResult(VERDICT_AGREEMENT, 0.5, f"near-miss ({prediction} vs {reference})")
    return ScoreResult(VERDICT_AGREEMENT, 0.0, f"mismatch ({prediction} vs {reference})")


def score_specificity(
    draft: CoverLetterDraft | None,
    *,
    dossier: CompanyDossier | None,
    empresa: str,
) -> ScoreResult | None:
    """Score draft specificity, reusing the draft-lint specificity rule.

    Args:
        draft: The generated draft, or ``None`` when none was produced.
        dossier: Company research dossier, or ``None`` if unavailable.
        empresa: Company name (the specificity rule needs it).

    Returns:
        ``ScoreResult`` (1.0 pass / 0.0 fail), or ``None`` when there is no draft
        to score.
    """
    if draft is None:
        return None
    issues = draft_lint.specificity_issues(draft.body, dossier, empresa)
    if issues:
        return ScoreResult(SPECIFICITY, 0.0, "; ".join(issues))
    return ScoreResult(SPECIFICITY, 1.0, "cita la empresa y un dato concreto del dossier")


class FaithfulnessJudge:
    """LLM-as-judge for factual faithfulness of the analysis/draft to the sources."""

    def __init__(self, client: AzureOpenAIClient) -> None:
        """Bind the judge to an Azure OpenAI client.

        Args:
            client: Client used for the ``gpt-4o`` judging call.
        """
        self._client = client

    async def score(
        self,
        *,
        oferta_text: str,
        dossier_text: str,
        reasoning: str,
        draft_body: str | None,
    ) -> ScoreResult:
        """Judge whether the analysis/draft invents facts not in the sources.

        Args:
            oferta_text: The offer rendered as text (source 1).
            dossier_text: The company dossier rendered as text (source 2).
            reasoning: The graph's fit ``reasoning`` to be judged.
            draft_body: The draft body to be judged, or ``None`` if absent.

        Returns:
            ``ScoreResult`` with value ``score / 100``.

        Raises:
            EvalError: If the judge returns an invalid ``FaithfulnessVerdict``.
        """
        system = prompt_loader.load_system(_FAITHFULNESS_PROMPT)
        user = prompt_loader.load_user(
            _FAITHFULNESS_PROMPT,
            oferta=oferta_text,
            dossier=dossier_text,
            razonamiento=reasoning,
            borrador=draft_body or "(sin borrador)",
        )
        result = await self._client.chat(
            deployment="4o",
            system=system,
            user=user,
            response_format=FaithfulnessVerdict,
            cacheable_system=True,
        )
        verdict = result.parsed
        if not isinstance(verdict, FaithfulnessVerdict):
            raise EvalError("Faithfulness judge did not return a valid FaithfulnessVerdict")

        comment = verdict.comment
        if verdict.unsupported_claims:
            comment = f"{comment} | unsupported: {'; '.join(verdict.unsupported_claims)}"
        logger.info(
            "eval_faithfulness_scored",
            score=verdict.score,
            unsupported=len(verdict.unsupported_claims),
        )
        return ScoreResult(FAITHFULNESS, verdict.score / 100, comment)
