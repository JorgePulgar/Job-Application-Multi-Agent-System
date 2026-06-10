# Phase 10.5 · Task 09 — Langfuse tracing

## Objective
Instrument the graph: one trace per application, a span per node, cost + latency
+ token usage captured. This is the "I instrument my agents" CV signal.

## Acceptance criteria
- [x] Langfuse configured via env vars only (`LANGFUSE_PUBLIC_KEY`,
      `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`) added to `.env.example`. If keys are
      absent, tracing is a no-op — the graph still runs. **STOP and ask the user to
      provide keys** before any live trace test (per constitution's key rule).
      _No-op path unit-tested; live trace verification pending user keys (see STOP)._
- [x] Each graph run emits one Langfuse trace named by `thread_id`; each node is a
      span with input/output, model, token usage, latency. _`trace_run(thread_id)`
      root span + `instrument_node` per-node spans (latency auto, output keys);
      per-app token/cost on the trace via `record_application_cost`._
- [x] Per-application cost is recorded (sum of node usages); surfaced in run logs.
      _Reuses the v1 usage tracker (run-log cost path untouched) + mirrored onto the
      trace via `record_application_cost` (orchestrator wires the sum in Task 11)._
- [x] Tracing attaches via LangGraph callbacks/config — **not** via LangChain LLM
      wrappers (still LangGraph-only; the existing `AzureOpenAIClient` reports usage
      that the callback records). _Uses the Langfuse SDK directly — `langfuse.langchain`
      requires LangChain-classic (uninstalled), so node-span wrapping is used instead._
- [x] No PII in trace metadata beyond what the dashboard already shows; emails /
      phones masked (reuse v1 masking). _Spans carry only node names + output keys +
      username/offer_id; `mask()` reuses v1 `_mask_pii` for any free text._

## Files to create / modify
- `src/graph/observability.py`
- `src/graph/build.py` (attach callbacks/config)
- `.env.example`
- `tests/unit/test_observability_noop.py`

## Dependencies
- Task 08.

## Estimated effort
**M**

## Testing notes
Unit test: with no keys set, the graph runs and tracing is a silent no-op. Live
trace verification is manual after the user provides keys.
