# Phase 9 · Task 02 — DB / drafts persistence strategy

## Objective
Decide and implement how the SQLite DB and `data/drafts/` persist across GitHub Actions runs.

## Acceptance criteria
- [x] **Propose two options** in a short note inside this task file (a `## Decision` section) and ask the user which to use BEFORE coding:
  - **Option A — Git branch**: a dedicated `data` branch in the same repo; the workflow checks it out into `data/` at start and commits + pushes back at end. Pros: easy to inspect history; the dashboard's local FastAPI can `git pull` the branch and serve fresh data. Cons: ties data to git history; binary churn.
  - **Option B — Workflow artifacts + release**: upload `state.db` and `drafts/` as artifacts; mirror the latest to a "rolling" GitHub Release attached to a fixed tag. Pros: cleaner repo. Cons: artifacts expire (90d default), restoring across cycles is fiddlier.
- [x] After user picks: implement the chosen strategy in the workflow. (Option A)
- [x] Document the recovery procedure in `docs/operations.md` (created here).
- [x] Ensure no secrets or PII land in commits/artifacts (DB path is fine; user YAMLs remain gitignored).

## Implementation notes
- `scripts/sync_data_branch.sh {pull|push}` uses a linked worktree at `.databranch/` (gitignored) so the code tree is untouched. First run creates an orphan `data` branch.
- Workflow: `contents: write`; "Restore runtime data" (pull) before migrations, "Persist runtime data" (push) after the run with `if: always() && not dry_run`.
- Verified end-to-end with a sandbox bare-repo origin: orphan creation → restore → incremental draft accumulation all roundtrip correctly.

## Decision

Two options were presented:

- **Option A — Git data branch**: dedicated `data` branch holding `state.db` +
  `drafts/`; the workflow restores it into `data/` at start and commits/pushes
  it back at end. Durable (no expiry), inspectable history, and the local
  dashboard can `git pull` it. Cons: binary churn in git history.
- **Option B — Workflow artifacts + rolling release**: cleaner repo, but
  artifacts expire (90d) and cross-run restore is fiddlier.

**Chosen: Option A** (user decision, 2026-06-06). Durability and easy local
refresh outweigh the binary-churn cost for this low-volume, 2-user system.

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
