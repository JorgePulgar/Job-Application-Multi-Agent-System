# Phase 10.5 · Task 02 — Pydantic fit schemas

## Objective
Add the structured-output models the graph nodes produce, per README §5.

## Acceptance criteria
- [ ] `src/models/fit.py` defines: `ParsedOffer`, `SponsorshipSignal`,
      `RequirementItem`, `RequirementMatch`, `FitAssessment`, `TailoringPointers`,
      `HumanDecision`, `CoverLetterDraft` — Pydantic v2, exactly per README §5.
- [ ] `FitAssessment.score` constrained `ge=0, le=100`; `recommendation` and
      `fit_level` are `Literal` types.
- [ ] `FitAssessment.to_evaluation_row(offer_id)` helper maps to the existing
      `evaluations` table row (score, reasoning, recommendation→`estado` mapping),
      reusing the v1 `Evaluation` model so the dashboard keeps working.
- [ ] All models have Google-style docstrings.
- [ ] Each model usable as `response_format=` with the existing
      `AzureOpenAIClient.chat` (no LangChain parsers).
- [ ] `mypy --strict src/models/fit.py` passes.

## Files to create / modify
- `src/models/fit.py`
- `tests/unit/test_fit_models.py`

## Dependencies
- Task 01.

## Estimated effort
**S**

## Testing notes
Validate round-trip from a sample JSON dict; assert `score` bounds reject 101;
assert `to_evaluation_row` produces a valid `Evaluation`.
