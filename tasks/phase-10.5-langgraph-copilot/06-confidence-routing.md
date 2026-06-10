# Phase 10.5 · Task 06 — Confidence routing + gather_more loop

## Objective
The conditional edge that makes this a graph, not a chain: SKIP ends short,
borderline/missing-info loops back for more research (max 2), confident proceeds
to human review.

## Acceptance criteria
- [x] `src/graph/nodes/route.py` implements `route_on_confidence(state) -> str`
      returning one of `"end"`, `"gather_more"`, `"human_review"`.
- [x] Routing logic:
      - `fit.recommendation == "skip"` → `"end"` (SKIP-is-short: no draft).
      - else if `fit.missing_info` non-empty **and** `loop_count < 2` →
        `"gather_more"`.
      - else → `"human_review"`.
- [x] `src/graph/nodes/gather_more.py` does targeted extra research for the
      `missing_info` items (reuse `search_web`/`CompanyResearcher`), increments
      `loop_count`, and routes back to `assess_fit`. _Uses `search_web` per item;
      folds snippets into `dossier.cultura_notas` so the next `assess_fit` sees them._
- [x] Loop cap is firm at 2 (mirrors the v1 max-2-regen rule). On exhaustion the
      offer proceeds to `human_review` with `missing_info` surfaced, never spins.
      _Cap enforced in the pure router (`loop_count < MAX_LOOPS=2`); termination
      test asserts exactly 2 passes then `human_review`._
- [x] Conditional edges wired in `src/graph/build.py`. _build_graph now takes
      `*, client, session_factory` and wires the real nodes 03-06; `human_review`
      (07) + `draft_cover_letter` (08) remain placeholders._

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
