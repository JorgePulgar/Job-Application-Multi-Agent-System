# Phase 8 · Task 08 — Local dev setup docs

## Objective
Make it dead simple for a future contributor (or future-Jorge) to run dashboard + API + Python pipeline locally.

## Acceptance criteria
- [x] `dashboard/README.md` documents: install (`pnpm install`), run (`pnpm dev`), env var (`NEXT_PUBLIC_API_URL`).
- [x] `api/README.md` documents: how to run (`uvicorn api.main:app --reload`), env vars consumed, DB location.
- [x] Root `README.md` references both (Phase 10 will expand it fully).
- [x] A make-or-task file (or `justfile` / `pnpm` script) to launch both servers in parallel for local dev (e.g. `pnpm dev` from `dashboard/` and `uvicorn` from project root; document, don't over-engineer).

## Implementation notes
- Chose the documented two-terminal approach (root README "Dashboard + API (local)" section) over a justfile/Makefile — no extra tooling dependency, per "don't over-engineer". Commands use `uv run uvicorn` (uvicorn isn't on PATH) and `pnpm`.
- api/README documents the real env it consumes: `CORS_ORIGINS`, `PROFILES_DIR`, DB at `data/state.db`, and `AZURE_OPENAI_*` only for the regenerate endpoint.

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
