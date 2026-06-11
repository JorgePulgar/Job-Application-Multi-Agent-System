# Phase 10.5 · Task 12 — Graph tests (unit + mocked integration)

## Objective
Lock the subgraph behavior with the repo's testing bar before closing the phase.

## Acceptance criteria
- [x] Each node has a unit test with mocked LLM/services (most added in Tasks
      03-08; this task fills gaps and adds the full-graph test).
      _All nodes covered: `test_node_ingest`, `test_node_research_fanout`
      (research/sponsorship/match), `test_node_assess_fit`, `test_routing`
      (gather_more + routing), `test_interrupt_resume` (human_review), `test_node_draft`._
- [x] One end-to-end integration test runs the **whole compiled graph** against
      mocked services for three offers: a clean APPLY, a borderline that triggers
      one `gather_more` loop then APPLY, and a hard SKIP that ends short (no draft).
      _`tests/integration/test_graph_end_to_end.py`: real `build_graph`, dispatching
      fake client + patched `CompanyResearcher.research`/`search_web`/`load_profile`._
- [x] Interrupt/resume covered (from Task 07) and kept green.
      _`test_interrupt_resume.py` (SqliteSaver durability) + the e2e auto-resume path._
- [x] `route_on_confidence` exhaustively tested (from Task 06).
      _`test_routing.py`: skip→end, loop0/loop1→gather_more, loop2 cap→human_review,
      clean→human_review._
- [x] All tests pass; `ruff check`, `ruff format --check`, and
      `mypy --strict src/graph/` pass.
      _489 passed (only 2 pre-existing scraper-credential failures, unrelated);
      ruff + mypy --strict src/graph/ clean._
- [x] No real network/LLM calls in the suite (respx / monkeypatch).
      _Fake Azure client + patched services; no respx needed (no HTTP reaches the wire)._

## Files to create / modify
- `tests/integration/test_graph_end_to_end.py`
- `tests/unit/` (gap-fill)

## Dependencies
- Task 11.

## Estimated effort
**M**

## Testing notes
The SKIP path must assert `draft is None` and that the draft node never ran. The
borderline path must assert `loop_count == 1` at completion.
