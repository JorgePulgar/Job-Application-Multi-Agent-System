# Phase 10.5 · Task 02 — Pydantic fit schemas

## Objective
Add the structured-output models the graph nodes produce, per README §5.

## Acceptance criteria
- [x] `src/models/fit.py` defines: `ParsedOffer`, `SponsorshipSignal`,
      `RequirementItem`, `RequirementMatch`, `FitAssessment`, `TailoringPointers`,
      `HumanDecision`, `CoverLetterDraft` — Pydantic v2, exactly per README §5.
- [x] `FitAssessment.score` constrained `ge=0, le=100`; `recommendation` and
      `fit_level` are `Literal` types.
- [x] `FitAssessment.to_evaluation_row(offer_id)` helper maps to the existing
      `evaluations` table row (score, reasoning, recommendation→`estado` mapping),
      reusing the v1 `Evaluation` model so the dashboard keeps working.
      _`recommendation`→`recomendacion` (apply/maybe/skip → aplicar/dudar/descartar);
      red_flags+missing_info stashed in `contras`. (`evaluations` has no `estado`
      column — the v1 verdict column is `recomendacion`.)_
- [x] All models have Google-style docstrings.
- [x] Each model usable as `response_format=` with the existing
      `AzureOpenAIClient.chat` (no LangChain parsers). _5 LLM-facing models verified
      via `openai.lib._pydantic.to_strict_json_schema`; `HumanDecision` is filled
      from the dashboard interrupt, not the LLM._
- [x] `mypy --strict src/models/fit.py` passes.

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
