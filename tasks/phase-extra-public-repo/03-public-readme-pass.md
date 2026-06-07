# Phase EXTRA · Task 03 — Public-facing README pass + badges

> ⚠️ **EXTRA / OPTIONAL phase.** Run only if/when going public.

## Objective
Make the landing README read well for a stranger / recruiter, not just for Jorge.

## Acceptance criteria
- [ ] Top-of-README: one-paragraph elevator pitch + the architecture mermaid
  diagram (or a rendered PNG fallback).
- [ ] Status badges where applicable: CI (daily-run workflow), Python version,
  license, code style (ruff). Only badges that actually reflect real state.
- [ ] "Screenshots" section embedding `docs/screenshots/*` (now they resolve once
  the repo is public).
- [ ] Clear "This is a personal/portfolio project — not accepting external PRs"
  note if that's Jorge's stance (confirm).
- [ ] Quickstart that works for a clean clone: prerequisites, `uv sync`, env setup,
  how to run one pipeline locally with mocked/sample data.
- [ ] Link to `docs/architecture.md` and `docs/operations.md`.
- [ ] Verify all relative links and image paths resolve on the rendered GitHub page.

## Implementation notes
- Keep bilingual structure (`README.md` ES + `README.en.md` EN) consistent.

## Files to create / modify
- `README.md`, `README.en.md`

## Dependencies
- Task 02

## Estimated effort
**M**

## Testing notes
Preview rendered markdown; click every link and image.
