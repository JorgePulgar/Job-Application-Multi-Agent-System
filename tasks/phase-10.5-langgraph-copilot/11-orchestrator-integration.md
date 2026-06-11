# Phase 10.5 · Task 11 — Orchestrator integration (feature-flagged) + DB persistence

## Objective
Wire the subgraph into the daily pipeline behind a flag, replacing the linear
`ViabilityEvaluator → ApplicationWriter` call-sites for the per-offer loop, and
persist results to the existing tables so the dashboard is unchanged.

## Acceptance criteria
- [x] Config flag `use_langgraph_eval` (default off) in the existing config layer.
      When on, the orchestrator invokes `evaluate_and_draft` per offer instead of
      calling `ViabilityEvaluator`/`ApplicationWriter` directly.
      _`Settings.use_langgraph_eval` (default `False`); stage-4 branch in
      `run_for_user` calls `Orchestrator._eval_draft_graph`, superseding both the
      v1 evaluate and write stages._
- [x] Per offer, the orchestrator builds initial state `{offer_id, username}` and
      invokes the compiled graph with the SqliteSaver + `thread_id`.
      _`build_graph(open_checkpointer(), client, session_factory=_shared)`;
      `thread_config(username, offer_id)`. Graph nodes share the orchestrator's
      session (no-commit factory) so SQLite never opens a second writer and research
      cache-hits; offers processed sequentially._
- [x] On graph completion: `FitAssessment.to_evaluation_row()` writes the
      `evaluations` row; `CoverLetterDraft` writes the `drafts` row;
      `needs_manual_context` maps to the existing draft state. Offer `estado`
      transitions match v1 semantics so the dashboard + FastAPI need no changes.
      _`_upsert_evaluation` (evaluada / razon_descarte on skip);
      `draft_persistence.save_graph_draft` (pendiente→borrador_generado, or
      needs_manual_context→stays evaluada). recomendacion stays aplicar/dudar/descartar._
- [~] Interrupts are surfaced in the run summary; a paused offer is resumable on
      the next run via its `thread_id` (the dashboard "review" action supplies the
      `HumanDecision`).
      _**DEFERRED BY DESIGN (decided with user 2026-06-11): Autonomous mode.** The
      orchestrator auto-resumes the `human_review` interrupt by mirroring the model's
      verdict, so drafts are produced unattended and HITL stays at draft-review in the
      dashboard (exactly v1) — this is what keeps AC#3/#5 "dashboard unchanged" true.
      `interrupt()` is retained in the graph; flipping to pause+resume is a small
      orchestrator change once a mid-pipeline review UI exists (separate task)._
- [x] With the flag off, v1 behavior is byte-for-byte unchanged.
      _Flag-off path is the original code verbatim; `test_flag_off_uses_v1_path`
      asserts the graph path is never called and the v1 evaluator runs._
- [x] `mypy --strict` passes on touched orchestrator code.
      _`mypy --strict` green on all 64 files; compiled graph annotated `Any` to avoid
      langgraph's RunnableConfig/Command overloads fighting a plain dict config._

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
