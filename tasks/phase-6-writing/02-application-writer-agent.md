# Phase 6 · Task 02 — ApplicationWriter agent

## Objective
For each offer with `recomendacion ∈ {aplicar, dudar}`, generate a `Draft` using `gpt-4o`.

## Acceptance criteria
- [ ] `src/agents/application_writer.py` implements `class ApplicationWriter` with `async def write(self, offer, company, evaluation, profile) -> Draft`.
- [ ] Structured outputs against `Draft`.
- [ ] Inputs include the **full user CV** in the system message (cached) — this is the primary use case for prompt caching.
- [ ] Per-call user message contains offer + dossier summary + evaluation pros/cons + a directive to pick 3-5 most relevant experiences.
- [ ] Returns the `Draft`. Lint and regeneration handled in Task 04 — this task focuses on the happy path generation.
- [ ] Updates offer `estado` to `draft_ready` once a valid draft is persisted (saving happens in Task 05).

## Files to create / modify
- `src/agents/application_writer.py`
- `tests/unit/test_application_writer.py`

## Dependencies
- Phase 3 / Task 01
- Phase 5 (evaluations must exist)
- Phase 6 / Task 01

## Estimated effort
**M**

## Testing notes
Mock LLM. Verify the CV is included in the system message (so prompt caching is meaningful) and that the parsed `Draft` is returned.
