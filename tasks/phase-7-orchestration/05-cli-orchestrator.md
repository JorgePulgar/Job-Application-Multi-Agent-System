# Phase 7 · Task 05 — CLI: orchestrator run

## Objective
Single command to run the whole pipeline for one user or all users.

## Acceptance criteria
- [x] `python -m src.cli orchestrator run --user jorge` runs the full pipeline.
- [x] `--all-users` iterates all profiles in `config/users/*.yaml` (excluding `.example`).
- [x] `--skip <stage>` flag (comma-separated, e.g. `scrape,research`) for re-running only later stages.
- [x] Exit code 0 if any user completed successfully; non-zero if all failed.
- [x] Printed summary per user and a global summary at the end.

## Files to create / modify
- `src/cli.py` (replace stub)

## Dependencies
- Phase 7 / Tasks 01-04

## Estimated effort
**S**

## Testing notes
Integration test runs against 2 mock profiles, mocked agents, verifies both completed and the global summary is correct.

## End of Phase 7
After this task: tell the user "Phase 7 complete. Run end-to-end against mocked LLM and verify. Approve to start Phase 8 (dashboard)."
