"""Typed state for the ``evaluate_and_draft`` subgraph (Phase 10.5).

``EvaluateDraftState`` is the shared channel object threaded through every node.
Branch outputs write disjoint keys (the research fan-out branches never write the
same key), so no custom reducers are needed beyond the fan-in node reading all
three branch results.

The structured-output schemas threaded through the state live in
``src/models/company.py`` (``CompanyDossier``, reused from v1) and
``src/models/fit.py`` (the Phase 10.5 fit schemas).
"""

from __future__ import annotations

from typing import TypedDict

from src.models.company import CompanyDossier
from src.models.fit import (
    CoverLetterDraft,
    FitAssessment,
    HumanDecision,
    ParsedOffer,
    RequirementMatch,
    SponsorshipSignal,
)


class EvaluateDraftState(TypedDict, total=False):
    """Shared state for the ``evaluate_and_draft`` subgraph.

    Attributes:
        offer_id: DB id of the offer under evaluation. Set by the caller.
        username: Profile username the evaluation is run for. Set by the caller.
        parsed: Structured offer parse. Set by ``ingest_offer``.
        dossier: Company research dossier. Set by ``research_company`` (reused
            from the v1 ``CompanyResearcher``).
        sponsorship: Visa/sponsorship + geo viability signal. Set by
            ``extract_sponsorship``.
        requirements: Requirement-by-requirement profile match. Set by
            ``match_profile``.
        fit: Final fit assessment + recommendation. Set by ``assess_fit``.
        loop_count: Number of confidence-loop passes taken. Set by
            ``route_on_confidence``.
        human_decision: Reviewer override + clarifications, or ``None`` before
            review. Set by ``human_review`` via ``interrupt()``.
        draft: Generated cover-letter draft, or ``None`` if not drafted. Set by
            ``draft_cover_letter``.
        needs_manual_context: ``True`` when the draft could not pass the
            prohibited-words/specificity post-check after the regen cap, so no
            draft is shipped and the offer is flagged for manual handling. Set by
            ``draft_cover_letter``.
    """

    offer_id: int
    username: str
    parsed: ParsedOffer
    dossier: CompanyDossier
    sponsorship: SponsorshipSignal
    requirements: RequirementMatch
    fit: FitAssessment
    loop_count: int
    human_decision: HumanDecision | None
    draft: CoverLetterDraft | None
    needs_manual_context: bool
