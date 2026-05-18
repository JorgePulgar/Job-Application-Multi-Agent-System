# Phase 5 · Task 01 — ViabilityEvaluation Pydantic model

## Objective
Schema for the viability evaluator's structured output, persisted to the `evaluations` table.

## Acceptance criteria
- [ ] `src/models/evaluation.py` defines `ViabilityEvaluation`: `score: int` (0-100), `ventajas: list[str]` (min 1, max 6), `desventajas: list[str]` (min 0, max 6), `red_flags_match: list[str]`, `recomendacion: Literal["aplicar", "dudar", "descartar"]`, `reasoning: str`.
- [ ] Validators: score in [0,100]; if `red_flags_match` non-empty, `recomendacion` must not be `aplicar`.
- [ ] Helper `to_db_row(offer_id: int) -> db.Evaluation`.

## Files to create / modify
- `src/models/evaluation.py`
- `tests/unit/test_evaluation_model.py`

## Dependencies
- Phase 1 complete

## Estimated effort
**S**

## Testing notes
Test the cross-field validator: red-flag match + `aplicar` should fail validation.
