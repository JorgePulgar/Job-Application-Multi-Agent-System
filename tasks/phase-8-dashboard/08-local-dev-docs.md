# Phase 8 · Task 08 — Local dev setup docs

## Objective
Make it dead simple for a future contributor (or future-Jorge) to run dashboard + API + Python pipeline locally.

## Acceptance criteria
- [ ] `dashboard/README.md` documents: install (`pnpm install`), run (`pnpm dev`), env var (`NEXT_PUBLIC_API_URL`).
- [ ] `api/README.md` documents: how to run (`uvicorn api.main:app --reload`), env vars consumed, DB location.
- [ ] Root `README.md` references both (Phase 10 will expand it fully).
- [ ] A make-or-task file (or `justfile` / `pnpm` script) to launch both servers in parallel for local dev (e.g. `pnpm dev` from `dashboard/` and `uvicorn` from project root; document, don't over-engineer).

## Files to create / modify
- `dashboard/README.md`
- `api/README.md`
- `README.md` (initial stub; full version in Phase 10)

## Dependencies
- Phase 8 / Tasks 01-07

## Estimated effort
**S**

## Testing notes
None. Verify by following your own instructions from a clean clone.

## End of Phase 8
After this task: tell the user "Phase 8 complete. Spin up the dashboard locally and click through `/`, `/drafts`, a draft detail, `/history`, `/settings`. Approve to start Phase 9 (automation)."
