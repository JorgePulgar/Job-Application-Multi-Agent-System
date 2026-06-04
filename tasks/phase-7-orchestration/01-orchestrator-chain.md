# Phase 7 · Task 01 — Orchestrator: scrape → filter → research → evaluate → write

## Objective
Chain the agents into a single per-user pipeline. The orchestrator decides parallelism; agents stay agnostic.

## Acceptance criteria
- [x] `src/orchestrator.py` exposes `class Orchestrator` with:
  - `async def run_for_user(self, username: str) -> RunResult`
  - `async def run_for_all_users(self) -> list[RunResult]`
- [x] Pipeline order: scrape → dedup → filter → research-companies (only for relevant offers) → evaluate (only with company researched) → write-drafts (only when recomendacion ∈ {aplicar, dudar}).
- [x] Concurrency: scraping uses `asyncio.gather` across platforms; filtering/research/evaluation/writing run sequentially over offers with bounded concurrency (default 3 in-flight).
- [x] `RunResult` aggregates per-stage counts and total tokens; passed to Task 03 for persistence.

## Files to create / modify
- `src/orchestrator.py`
- `tests/integration/test_orchestrator_pipeline.py`

## Dependencies
- Phases 1-6 complete

## Estimated effort
**L**

## Testing notes
Integration test: in-memory SQLite seeded with a fake user, all agents mocked with deterministic responses, run the full pipeline end-to-end, assert final DB state and `RunResult` contents.
