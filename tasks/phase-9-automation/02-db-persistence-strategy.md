# Phase 9 · Task 02 — DB / drafts persistence strategy

## Objective
Decide and implement how the SQLite DB and `data/drafts/` persist across GitHub Actions runs.

## Acceptance criteria
- [ ] **Propose two options** in a short note inside this task file (a `## Decision` section) and ask the user which to use BEFORE coding:
  - **Option A — Git branch**: a dedicated `data` branch in the same repo; the workflow checks it out into `data/` at start and commits + pushes back at end. Pros: easy to inspect history; the dashboard's local FastAPI can `git pull` the branch and serve fresh data. Cons: ties data to git history; binary churn.
  - **Option B — Workflow artifacts + release**: upload `state.db` and `drafts/` as artifacts; mirror the latest to a "rolling" GitHub Release attached to a fixed tag. Pros: cleaner repo. Cons: artifacts expire (90d default), restoring across cycles is fiddlier.
- [ ] After user picks: implement the chosen strategy in the workflow.
- [ ] Document the recovery procedure in `docs/operations.md` (created here).
- [ ] Ensure no secrets or PII land in commits/artifacts (DB path is fine; user YAMLs remain gitignored).

## Files to create / modify
- `.github/workflows/daily-run.yml` (extend)
- `docs/operations.md`
- (If Option A) helper script in `scripts/sync_data_branch.sh`

## Dependencies
- Phase 9 / Task 01

## Estimated effort
**M** once the decision is made.

## Testing notes
Dry run on a throwaway branch.
