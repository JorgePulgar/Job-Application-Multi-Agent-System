"""Typed state for the ``evaluate_and_draft`` subgraph (Phase 10.5).

``EvaluateDraftState`` is the shared channel object threaded through every node.
Branch outputs write disjoint keys (the research fan-out branches never write the
same key), so no custom reducers are needed beyond the fan-in node reading all
three branch results.

The six structured-output schemas referenced below (``ParsedOffer``,
``SponsorshipSignal``, ``RequirementMatch``, ``FitAssessment``,
``HumanDecision``, ``CoverLetterDraft``) are created in ``src/models/fit.py`` in
Task 02. Until then they are aliased to ``Any`` here so this scaffold type-checks
and the graph compiles; Task 02 replaces the aliases with concrete imports.
"""

from __future__ import annotations

from typing import Any, TypedDict

from src.models.company import CompanyDossier

# Placeholders, replaced by concrete imports from ``src.models.fit`` in Task 02.
ParsedOffer = Any
SponsorshipSignal = Any
RequirementMatch = Any
FitAssessment = Any
HumanDecision = Any
CoverLetterDraft = Any


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
