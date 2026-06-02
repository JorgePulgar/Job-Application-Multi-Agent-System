# Phase 6 · Task 03 — Writer prompt (Spanish, strict rules)

## Objective
The actual prompt text. Encodes the prohibited-words list, specificity rule, no-AI-disclosure rule, and tone.

## Acceptance criteria
- [x] `src/prompts/application_writer.system.md` (Spanish):
  - Role: writer crafting tailored job application emails for Spanish-speaking AI/data candidates in Spain.
  - Hard rules: avoid the prohibited words list verbatim (list inline), must include at least one company-specific concrete reference, must NOT disclose AI assistance, tone is professional + warm + concise.
  - If a specific hook can't be found, return `needs_manual_context=true` with `flagged_reasons` filled in.
  - User CV placeholder `{{cv_summary}}` (this is what gets cached).
- [x] `src/prompts/application_writer.user.md`: variables `{{titulo}}`, `{{empresa}}`, `{{ubicacion}}`, `{{modalidad}}`, `{{descripcion}}`, `{{dossier_summary}}`, `{{evaluation_ventajas}}`, `{{evaluation_desventajas}}`, `{{target_roles}}`.
- [x] Few-shot examples (1-2) of correct outputs, in Spanish, demonstrating specificity.
- [x] Prompt itself contains no prohibited words.

## Files to create / modify
- `src/prompts/application_writer.system.md`
- `src/prompts/application_writer.user.md`

## Dependencies
- Phase 3 / Task 01

## Estimated effort
**M**

## Testing notes
Unit test loads the prompt and asserts: contains the prohibited words list, does not itself contain those words in the model-facing examples, and successfully interpolates all variables.
