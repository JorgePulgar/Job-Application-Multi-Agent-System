# Phase 10.5 · Task 12 — Graph tests (unit + mocked integration)

## Objective
Lock the subgraph behavior with the repo's testing bar before closing the phase.

## Acceptance criteria
- [ ] Each node has a unit test with mocked LLM/services (most added in Tasks
      03-08; this task fills gaps and adds the full-graph test).
- [ ] One end-to-end integration test runs the **whole compiled graph** against
      mocked services for three offers: a clean APPLY, a borderline that triggers
      one `gather_more` loop then APPLY, and a hard SKIP that ends short (no draft).
- [ ] Interrupt/resume covered (from Task 07) and kept green.
- [ ] `route_on_confidence` exhaustively tested (from Task 06).
- [ ] All tests pass; `ruff check`, `ruff format --check`, and
      `mypy --strict src/graph/` pass.
- [ ] No real network/LLM calls in the suite (respx / monkeypatch).

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
