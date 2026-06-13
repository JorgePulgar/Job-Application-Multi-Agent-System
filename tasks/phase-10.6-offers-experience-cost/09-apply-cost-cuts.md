# Phase 10.6 · Task 09 — Apply targeted cost cuts + re-measure

## Objective
Implement the optimization candidates ranked highest in Task 08 and prove they cut
€/offer **without** regressing draft quality, using the Phase 10.5 eval set as the
guardrail.

## Acceptance criteria
- [ ] Each change is one of the Task 08 candidates (no speculative optimizations
      outside that list). Likely set, subject to the report: fix any prompt-cache
      miss on system message + CV; correct any node on the wrong deployment
      (`gpt-4o` → `gpt-4o-mini` where reasoning is mechanical); trim research
      fan-out / `gather_more` where the report shows poor cost/value.
- [ ] Behavior preserved: prompts still load from `src/prompts/*.md`, LLM calls
      stay in `src/services/`, prohibited-words + specificity checks still run,
      `needs_manual_context` path intact. No prompt text moved inline.
- [ ] Re-run the eval dataset before vs after: record new €/offer and
      faithfulness/quality scores. Quality must not drop below baseline within a
      stated tolerance. Append before/after numbers to `COST-BASELINE.md`.
- [ ] Net measured cost reduction reported (a real, stated % — even modest — not
      "should be cheaper"). A candidate that fails to save or hurts quality is
      reverted and noted.
- [ ] `mypy --strict` + `ruff` pass on touched code; existing graph/agent unit +
      integration tests stay green.

## Implementation notes
- Touch the **active path** (`src/graph/` nodes, `src/services/azure_openai.py`,
  `usage_tracker`). v1 `ViabilityEvaluator`/`ApplicationWriter` are reference-only
  behind the flag — touch only if the report flags them.
- Prompt caching is an Azure OpenAI / `openai` SDK feature — verify the cache is
  actually engaged (stable prefix, sufficient length) before claiming a fix. Look
  it up if unfamiliar; do not invent the API.
- Keep changes small + individually revertible so a quality regression bisects to
  one change.

## Files to create / modify
- `src/graph/nodes/*` and/or `src/services/azure_openai.py` (per Task 08)
- `src/graph/evals.py` (if the re-measure needs a runner tweak)
- `tasks/phase-10.6-offers-experience-cost/COST-BASELINE.md` (append before/after)

## Dependencies
- Task 08 (ranked candidate list + baseline numbers).

## Estimated effort
**M–L**

## Testing notes
The eval re-run **is** the test: before/after €/offer + quality. Existing graph
unit + mocked-integration suites stay green. No quality regression beyond the
stated tolerance, or the offending change is reverted.
