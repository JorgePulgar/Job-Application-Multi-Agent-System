# Phase 7 · Task 04 — Token / cost tracking

## Objective
Centralized token accounting so we can show a cost estimate per run.

## Acceptance criteria
- [x] `src/services/usage_tracker.py` exposes `class UsageTracker` with `record(deployment, prompt_tokens, cached_tokens, completion_tokens)` and `summary()` returning per-deployment totals.
- [x] `AzureOpenAIClient.chat` accepts an injected tracker and records each call's usage.
- [x] Costs computed via a `PRICING` constant per 1M tokens (Azure list price snapshot, documented in code with date and link). Reduced rate applied to `cached_tokens`.
- [x] Orchestrator instantiates one tracker per run and writes the summary into `run_logs.tokens_consumidos` and `coste_estimado_eur`.
- [x] Pricing is editable in one place; tests cover the math.

## Files to create / modify
- `src/services/usage_tracker.py`
- `src/services/azure_openai.py` (extend Phase 3 / Task 01)
- `tests/unit/test_usage_tracker.py`

## Dependencies
- Phase 7 / Tasks 01-03

## Estimated effort
**M**

## Testing notes
Test that `cached_tokens` are billed differently from `prompt_tokens`. Round to 4 decimal EUR.
