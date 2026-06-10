# Phase 10.5 · Task 06 — Confidence routing + gather_more loop

## Objective
The conditional edge that makes this a graph, not a chain: SKIP ends short,
borderline/missing-info loops back for more research (max 2), confident proceeds
to human review.

## Acceptance criteria
- [ ] `src/graph/nodes/route.py` implements `route_on_confidence(state) -> str`
      returning one of `"end"`, `"gather_more"`, `"human_review"`.
- [ ] Routing logic:
      - `fit.recommendation == "skip"` → `"end"` (SKIP-is-short: no draft).
      - else if `fit.missing_info` non-empty **and** `loop_count < 2` →
        `"gather_more"`.
      - else → `"human_review"`.
- [ ] `src/graph/nodes/gather_more.py` does targeted extra research for the
      `missing_info` items (reuse `search_web`/`CompanyResearcher`), increments
      `loop_count`, and routes back to `assess_fit`.
- [ ] Loop cap is firm at 2 (mirrors the v1 max-2-regen rule). On exhaustion the
      offer proceeds to `human_review` with `missing_info` surfaced, never spins.
- [ ] Conditional edges wired in `src/graph/build.py`.

## Files to create / modify
- `src/graph/nodes/route.py`
- `src/graph/nodes/gather_more.py`
- `src/graph/build.py` (wire edges)
- `tests/unit/test_routing.py`

## Dependencies
- Task 05.

## Estimated effort
**M**

## Testing notes
Unit-test the pure router on crafted states: skip→end; missing_info+loop0→
gather_more; missing_info+loop2→human_review; clean confident→human_review.
Assert no infinite loop.
