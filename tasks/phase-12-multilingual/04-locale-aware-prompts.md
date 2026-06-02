# Phase 12 · Task 04 — Locale-aware prompt loader + English prompts

> **v2 scope.** Requires explicit user approval after v1 + v1.1. This is the task that lifts the v1 "all prompts in Spanish" rule — only for v2, and only behind the language config.

## Objective
Let prompts exist per language and pick the right one at runtime. v1 keeps Spanish as the default; v2 adds English variants for filter, researcher, evaluator, and writer.

## Acceptance criteria
- [ ] `prompt_loader` supports a `lang` parameter and resolves `{{name}}.{{lang}}.system.md` (e.g. `application_writer.en.system.md`), falling back to the existing Spanish files when `lang="es"` (no rename of v1 files — `es` is the default/no-suffix variant).
- [ ] English variants created for: `offer_filter`, `company_researcher`, `viability_evaluator`, `application_writer` (system + user).
- [ ] English prohibited-words list encoded (e.g. "passionate", "team player", "results-oriented", "proactive") with the same post-generation lint enforcement as Spanish.
- [ ] Agents pass the draft/working language through to the loader.
- [ ] Prompt unit tests assert EN interpolation + that EN examples are clean of the EN prohibited words.

## Files to create / modify
- `src/services/prompt_loader.py`
- `src/prompts/*.en.system.md`, `*.en.user.md`
- `src/agents/*` (thread `lang` through)
- `tests/unit/...`

## Dependencies
- Phase 12 / Task 01

## Estimated effort
**L**
