# Phase 10.5 · Task 10 — Eval dataset + faithfulness/quality scores

## Objective
Build a Langfuse eval dataset from past offers/evaluations and score the graph's
verdicts and drafts, so improvements across versions are provable. This is the
seniority signal: "I evaluate my agents," not just "I built one."

## Acceptance criteria
- [ ] Export script `scripts/build_eval_dataset.py` pulls historical offers +
      their v1 evaluations (and any human-decided outcomes) from SQLite into a
      Langfuse dataset (or a local JSONL if Langfuse keys absent).
- [ ] Dataset items contain the offer input + a reference label (the v1 verdict or
      a hand-corrected one).
- [ ] An eval run executes the subgraph over the dataset and scores:
      - **Verdict agreement** vs reference (apply/maybe/skip).
      - **Faithfulness** of `reasoning`/draft to the offer + dossier (no invented
        facts) — LLM-as-judge, `gpt-4o`.
      - **Specificity** of drafts (≥1 concrete company fact).
- [ ] Scores recorded to Langfuse (or printed + saved to `data/evals/` if no keys).
- [ ] A short `docs/eval-baseline.md` records the first run's numbers as the
      baseline to beat.

## Files to create / modify
- `scripts/build_eval_dataset.py`
- `scripts/run_eval.py`
- `src/graph/evals.py` (scorers)
- `docs/eval-baseline.md`
- `tests/unit/test_eval_scorers.py`

## Dependencies
- Task 09.

## Estimated effort
**L**

## Testing notes
Unit-test scorers on crafted (prediction, reference) pairs: exact-match verdict
scorer; a faithfulness judge mocked to return a score; assert dataset builder
emits valid items from a seeded test DB.
