# Phase 10.5 · Task 10 — Eval dataset + faithfulness/quality scores

## Objective
Build a Langfuse eval dataset from past offers/evaluations and score the graph's
verdicts and drafts, so improvements across versions are provable. This is the
seniority signal: "I evaluate my agents," not just "I built one."

## Acceptance criteria
- [x] Export script `scripts/build_eval_dataset.py` pulls historical offers +
      their v1 evaluations (and any human-decided outcomes) from SQLite into a
      Langfuse dataset (or a local JSONL if Langfuse keys absent).
      _`build_items()` joins offers↔evaluations; always writes `data/evals/dataset.jsonl`,
      and also pushes to a Langfuse dataset (`create_dataset`/`create_item`) when keys present._
- [x] Dataset items contain the offer input + a reference label (the v1 verdict or
      a hand-corrected one).
      _`EvalItem.input` = offer fields (offer_id/username/titulo/empresa/…),
      `expected_output` = v1 `recomendacion` mapped to apply/maybe/skip; JSONL is
      hand-correctable._
- [x] An eval run executes the subgraph over the dataset and scores:
      - **Verdict agreement** vs reference (apply/maybe/skip).
      - **Faithfulness** of `reasoning`/draft to the offer + dossier (no invented
        facts) — LLM-as-judge, `gpt-4o`.
      - **Specificity** of drafts (≥1 concrete company fact).
      _`scripts/run_eval.py` runs the subgraph per item (auto-resumes the HITL
      interrupt mirroring the model verdict). Scorers in `src/graph/evals.py`:
      `score_verdict_agreement` (1/0.5/0), `FaithfulnessJudge` (gpt-4o + new
      `eval_faithfulness` prompt), `score_specificity` (reuses draft-lint)._
- [x] Scores recorded to Langfuse (or printed + saved to `data/evals/` if no keys).
      _Each item runs inside `trace_run`; `score_current_trace` when enabled. Always
      prints the aggregate + saves `data/evals/eval-<ts>.json`._
- [x] A short `docs/eval-baseline.md` records the first run's numbers as the
      baseline to beat.
      _Committed with methodology + a "pending first live run" table; `run_eval.py
      --write-baseline` overwrites it with real numbers (live run gated on keys,
      per the constitution key rule)._

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
