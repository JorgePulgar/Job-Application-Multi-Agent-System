# Phase 10.6 · Task 08 — Cost baseline read (Langfuse)

## Objective
Produce a data-grounded picture of where per-offer LLM spend goes, using the
Phase 10.5 Langfuse traces + `usage_tracker`, so Task 09 cuts cost where it
actually is — not by guesswork. **Analysis + reporting only; no behavior changes.**

## Acceptance criteria
- [x] Report committed as
      `tasks/phase-10.6-offers-experience-cost/COST-BASELINE.md` covering, for a
      representative eval/sample run: total cost, cost & tokens **per graph node**
      (ingest / research_company / extract_sponsorship / match_profile /
      assess_fit / gather_more / draft_cover_letter), and cost per offer
      end-to-end.
- [x] Prompt-cache effectiveness reported: cache-hit ratio on the stable system
      messages + user CV (what CLAUDE.md §4 requires cached). Flag any node where
      caching is silently NOT hitting.
- [x] Model-routing audit: confirm each node's deployment (`gpt-4o-mini` vs
      `gpt-4o`) and flag any mechanical node wrongly on `gpt-4o` or vice-versa.
- [x] Confidence-loop (`gather_more`, max 2) cost quantified: how often it fires +
      marginal cost — candidate for trimming.
- [x] Report ends with a ranked list of concrete optimization candidates (highest
      €/offer saving first), each tagged feasible / risky-to-quality. This list is
      the input contract for Task 09.

## Implementation notes
- Data already exists: `src/graph/observability.py` (Langfuse),
  `src/services/usage_tracker.py`, and the Phase 10.5 task-10 eval set. Pull
  numbers via the Langfuse skill/CLI or local usage-tracker output — no new
  instrumentation here.
- If trace data is thin, run the existing eval dataset to generate a clean sample
  and say so in the report.
- No agent/graph code changes. A measurement gap (e.g. cost not attributed per
  node) is logged as a Task 09 prerequisite, not fixed here.

## Files to create / modify
- `tasks/phase-10.6-offers-experience-cost/COST-BASELINE.md` (new)

## Dependencies
- Phase 10.5 tasks 09 (Langfuse) + 10 (eval dataset). Independent of 01–07.

## Estimated effort
**S–M**

## Testing notes
No tests — analysis task. "Done" = report exists, numbers trace to a named run,
ranked candidate list is actionable for Task 09.
