"""Structured-output schemas for the ``evaluate_and_draft`` subgraph (Phase 10.5).

These Pydantic v2 models are what the graph nodes emit. The LLM-produced ones
(``ParsedOffer``, ``SponsorshipSignal``, ``RequirementMatch``, ``FitAssessment``,
``CoverLetterDraft``) are passed directly as ``response_format=`` to
``AzureOpenAIClient.chat`` — no LangChain parsers. ``HumanDecision`` is filled
from the dashboard via the graph ``interrupt()``, not by the model.

``FitAssessment`` supersedes the v1 ``ViabilityEvaluation`` on the graph path;
``FitAssessment.to_evaluation_row`` maps it back onto the existing
``evaluations`` table so the dashboard/API contract is untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from src.db.models import Evaluation as DbEvaluation


class ParsedOffer(BaseModel):
    """Structured parse of a raw job offer, emitted by ``ingest_offer``.

    Attributes:
        title: Job title as stated in the offer.
        detected_language: Offer language; drives downstream analysis + draft
            language (``"es"`` -> Spanish, ``"en"`` -> English).
        seniority: Stated seniority ("junior"/"mid"/"senior") or ``None`` if not
            stated. Do not infer.
        company: Hiring company name.
        sector: Industry sector, or ``None`` if not stated.
        location: Work location, or ``None`` if not stated.
        remote_policy: Remote / hybrid / onsite / not stated.
        required_skills: Hard requirements pulled from the offer.
        preferred_skills: Nice-to-have skills pulled from the offer.
        salary_raw: Salary text verbatim, or ``None`` if absent.
        languages: Languages the role asks for.
        contract_type: Contract type, or ``None`` if not stated.
        sponsorship_mention: Verbatim visa/sponsorship text, or ``None``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str
    detected_language: Literal["es", "en"]
    seniority: str | None
    company: str
    sector: str | None
    location: str | None
    remote_policy: str | None
    required_skills: list[str]
    preferred_skills: list[str]
    salary_raw: str | None
    languages: list[str]
    contract_type: str | None
    sponsorship_mention: str | None


class SponsorshipSignal(BaseModel):
    """Visa/sponsorship and geographic viability signal, from ``extract_sponsorship``.

    Attributes:
        needs_sponsorship: Whether the role appears to need work-permit
            sponsorship for the candidate; ``None`` if it cannot be told.
        sponsorship_offered: Whether the employer offers sponsorship; ``None`` if
            it cannot be told.
        geo_viable_for_spain: Whether the role is reachable from Spain
            (remote-EU or relocation possible).
        working_language: Day-to-day working language, or ``None`` if unknown.
        blocker: Decisive blocker text if one exists, else ``None``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    needs_sponsorship: bool | None
    sponsorship_offered: bool | None
    geo_viable_for_spain: bool
    working_language: str | None
    blocker: str | None


RequirementStatus = Literal["met", "partial", "missing"]


class RequirementItem(BaseModel):
    """A single requirement matched against the user's profile.

    Attributes:
        requirement: The requirement text from the offer.
        status: Whether the user meets it fully, partially, or not at all.
        note: Short justification for the status.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    requirement: str
    status: RequirementStatus
    note: str


class RequirementMatch(BaseModel):
    """Requirement-by-requirement profile match, from ``match_profile``.

    Attributes:
        items: Per-requirement match results.
        standout_points: Where the user stands out for this specific role.
        gaps: Requirements the user does not meet.
    """

    items: list[RequirementItem]
    standout_points: list[str]
    gaps: list[str]


FitLevel = Literal["strong", "moderate", "weak"]
Recommendation = Literal["apply", "maybe", "skip"]


class TailoringPointers(BaseModel):
    """Guidance for tailoring the application, present only when apply/maybe.

    Attributes:
        cv_emphasis: CV points to emphasise for this role.
        cover_letter_hook: The concrete hook the cover letter should open on.
        gap_to_address: A gap worth addressing head-on, or ``None``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    cv_emphasis: list[str]
    cover_letter_hook: str
    gap_to_address: str | None


class FitAssessment(BaseModel):
    """Final fit verdict for an offer, from ``assess_fit``.

    Supersedes the v1 ``ViabilityEvaluation`` on the graph path. Maps back to the
    ``evaluations`` table via :meth:`to_evaluation_row`.

    Attributes:
        fit_level: Qualitative fit (strong / moderate / weak).
        recommendation: Action recommendation (apply / maybe / skip).
        score: Numeric fit score, 0-100.
        reasoning: One or two sentences giving the decisive reason.
        red_flags: Hard concerns found during assessment.
        missing_info: Unknowns that drive the confidence loop.
        tailoring: Tailoring pointers when apply/maybe, else ``None``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    fit_level: FitLevel
    recommendation: Recommendation
    score: int = Field(ge=0, le=100, description="Fit score 0-100.")
    reasoning: str
    red_flags: list[str]
    missing_info: list[str]
    tailoring: TailoringPointers | None

    def to_evaluation_row(self, offer_id: int) -> DbEvaluation:
        """Map to an unsaved ``evaluations`` ORM row, reusing the v1 model.

        Keeps the dashboard/API contract intact: persists ``score`` ->
        ``puntuacion``, ``reasoning`` -> ``razonamiento``, and
        ``recommendation`` -> the Spanish ``recomendacion`` the v1 schema uses.
        ``red_flags`` and ``missing_info`` are stashed in the JSON ``contras``
        column.

        Args:
            offer_id: FK to the evaluated offer.

        Returns:
            Unsaved ``db.Evaluation`` instance ready for ``session.add()``.
        """
        from src.db.models import Evaluation as DbEvaluation  # avoid circular at runtime

        recomendacion = _RECOMMENDATION_TO_RECOMENDACION[self.recommendation]
        return DbEvaluation(
            offer_id=offer_id,
            puntuacion=self.score,
            pros=None,
            contras={"red_flags": self.red_flags, "missing_info": self.missing_info},
            recomendacion=recomendacion,
            razonamiento=self.reasoning,
        )


# FitAssessment.recommendation (English) -> v1 evaluations.recomendacion (Spanish).
_RECOMMENDATION_TO_RECOMENDACION: dict[Recommendation, str] = {
    "apply": "aplicar",
    "maybe": "dudar",
    "skip": "descartar",
}


class HumanDecision(BaseModel):
    """Reviewer override captured by ``human_review`` via ``interrupt()``.

    Filled from the dashboard, not the model.

    Attributes:
        decision: The reviewer's recommendation, overriding the model's.
        lead_angle: Angle the reviewer wants the draft to lead with, or ``None``.
        clarifications: Answers keyed by the interrupt question they respond to.
    """

    decision: Recommendation
    lead_angle: str | None
    clarifications: dict[str, str]


class CoverLetterDraft(BaseModel):
    """Generated cover-letter draft, from ``draft_cover_letter``.

    Attributes:
        subject: Email subject line.
        body: Draft body (email + cover letter), in the offer's language.
        lead_angle: The angle the draft leads with.
        hook: The concrete company/role fact the draft hooks onto.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str
    body: str
    lead_angle: str
    hook: str
