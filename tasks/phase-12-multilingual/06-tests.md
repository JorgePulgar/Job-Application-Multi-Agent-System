# Phase 12 · Task 06 — Multilingual / multi-country tests

> **v2 scope.** Requires explicit user approval after v1 + v1.1.

## Objective
End-to-end coverage of the multi-country + bilingual path with mocked services.

## Acceptance criteria
- [ ] Scraper tests: a profile with `target_countries=["es","gb"]` hits the correct per-country endpoints (mocked) and merges/dedups results.
- [ ] Prompt tests: EN variants interpolate all variables and EN examples contain no EN prohibited words.
- [ ] Lint test: EN prohibited word in a generated draft triggers regeneration / `needs_manual_context`, same as Spanish.
- [ ] Integration test: full pipeline for an English posting produces an English draft tagged `idioma="en"`.
- [ ] Backward-compat test: a v1-style Spain/Spanish profile produces identical behavior to before Phase 12.

## Files to create / modify
- `tests/unit/...`, `tests/integration/...`

## Dependencies
- Phase 12 / Task 01–05

## Estimated effort
**M**
