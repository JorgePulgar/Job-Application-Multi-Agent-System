# Phase 5 · Task 02 — ViabilityEvaluator agent

## Objective
For each offer in `researching` state with a researched company, compute a `ViabilityEvaluation` using `gpt-4o`.

## Acceptance criteria
- [x] `src/agents/viability_evaluator.py` implements `class ViabilityEvaluator` with `async def evaluate(self, offer: db.Offer, company: db.Company, profile: UserProfile) -> ViabilityEvaluation`.
- [x] Structured outputs against `ViabilityEvaluation`.
- [x] Spanish prompt in `src/prompts/viability_evaluator.{system,user}.md`. Few-shot with 2-3 examples covering recommend / doubt / discard.
- [x] Inputs include: offer title/description/salary/modalidad/ubicacion, the dossier's `to_summary_for_prompt()`, the profile's targets, red flags, salary minimum.
- [x] Writes the evaluation to the `evaluations` table and updates offer `estado` to `evaluated`.

## Files to create / modify
- `src/agents/viability_evaluator.py`
- `src/prompts/viability_evaluator.system.md`
- `src/prompts/viability_evaluator.user.md`
- `tests/unit/test_viability_evaluator.py`

## Dependencies
- Phase 3 / Task 01
- Phase 4 (companies must be researched first)
- Phase 5 / Task 01

## Estimated effort
**M**

## Testing notes
Mock LLM; verify DB row creation, offer state transition, and the cross-field rule (no `aplicar` with red flags).
