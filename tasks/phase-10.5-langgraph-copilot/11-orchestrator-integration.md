# Phase 10.5 · Task 11 — Orchestrator integration (feature-flagged) + DB persistence

## Objective
Wire the subgraph into the daily pipeline behind a flag, replacing the linear
`ViabilityEvaluator → ApplicationWriter` call-sites for the per-offer loop, and
persist results to the existing tables so the dashboard is unchanged.

## Acceptance criteria
- [ ] Config flag `use_langgraph_eval` (default off) in the existing config layer.
      When on, the orchestrator invokes `evaluate_and_draft` per offer instead of
      calling `ViabilityEvaluator`/`ApplicationWriter` directly.
- [ ] Per offer, the orchestrator builds initial state `{offer_id, username}` and
      invokes the compiled graph with the SqliteSaver + `thread_id`.
- [ ] On graph completion: `FitAssessment.to_evaluation_row()` writes the
      `evaluations` row; `CoverLetterDraft` writes the `drafts` row;
      `needs_manual_context` maps to the existing draft state. Offer `estado`
      transitions match v1 semantics so the dashboard + FastAPI need no changes.
- [ ] Interrupts are surfaced in the run summary; a paused offer is resumable on
      the next run via its `thread_id` (the dashboard "review" action supplies the
      `HumanDecision`).
- [ ] With the flag off, v1 behavior is byte-for-byte unchanged.
- [ ] `mypy --strict` passes on touched orchestrator code.

## Files to create / modify
- `src/orchestrator.py`
- `src/config.py` (flag)
- `api/` (only if the resume action needs an endpoint — keep contract stable)
- `tests/integration/test_orchestrator_langgraph.py`

## Dependencies
- Task 10.

## Estimated effort
**L**

## Testing notes
Integration test with mocked services: flag on → graph path persists an evaluation
+ draft row with the same shape v1 produces; flag off → existing path untouched.
Assert dashboard-facing columns identical between paths for an equivalent offer.
