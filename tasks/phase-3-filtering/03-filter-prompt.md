# Phase 3 · Task 03 — Spanish filter prompt with few-shot

## Objective
The actual prompt used by `OfferFilter`. Spanish, with few-shot examples covering edge cases.

## Acceptance criteria
- [x] `src/prompts/offer_filter.system.md` — system prompt explaining the task, decision rules, and that the response MUST be JSON matching the `FilterDecision` schema. Spanish.
- [x] `src/prompts/offer_filter.user.md` — user template with `{{titulo}}`, `{{empresa}}`, `{{ubicacion}}`, `{{modalidad}}`, `{{descripcion}}`, `{{target_roles}}`, `{{target_sectors}}`, `{{red_flags}}`, `{{location_preference}}`.
- [x] Few-shot examples (3-5) covering: clear relevant, clear discard, ambiguous senior-level for a junior profile, body-shopping consultancy, location mismatch.
- [x] No prohibited words appear in the prompt (consistency).
- [x] Prompt is loaded via `prompt_loader.load("offer_filter")`, not hardcoded.

## Files to create / modify
- `src/prompts/offer_filter.system.md`
- `src/prompts/offer_filter.user.md`

## Dependencies
- Phase 3 / Task 01

## Estimated effort
**S**

## Testing notes
No code, but verify the template variables resolve cleanly through `prompt_loader.load` with sample data. Add a unit test that loading the prompt succeeds and contains the expected variables.
