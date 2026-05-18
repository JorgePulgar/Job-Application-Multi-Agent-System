# Phase 6 · Task 04 — Post-generation lint + regeneration

## Objective
After the LLM returns a draft, lint it for prohibited words and specificity. On failure, regenerate up to 2 times, then flag.

## Acceptance criteria
- [ ] `src/services/draft_lint.py` exposes:
  - `lint(draft: Draft, company: CompanyDossier) -> LintResult` where `LintResult` is `{ok: bool, issues: list[str]}`.
  - Checks: no prohibited word (case-insensitive, accent-folded); body references at least one concrete fact from the dossier (company name + at least one of: product, tech, location, recent news token); no AI-disclosure language (`IA`, `inteligencia artificial`, `asistente AI`, etc. in body).
- [ ] `ApplicationWriter.write` integrates `lint`: on failure, regenerates with the failure reasons added to the user message; max 2 retries; if still failing, returns `Draft(needs_manual_context=True, flagged_reasons=[...])` without raising.
- [ ] Lint runs are logged structurally (no draft body in logs — just a hash + reason).

## Files to create / modify
- `src/services/draft_lint.py`
- `src/agents/application_writer.py` (extend Task 02)
- `tests/unit/test_draft_lint.py`

## Dependencies
- Phase 6 / Tasks 01, 02, 03

## Estimated effort
**M**

## Testing notes
Hand-craft drafts triggering each rule (prohibited word, no specific reference, AI disclosure). Verify the agent retries and eventually flags.
