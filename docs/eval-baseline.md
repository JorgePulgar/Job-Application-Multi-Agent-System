# Eval baseline — `evaluate_and_draft` subgraph

The Phase 10.5 subgraph is scored against a dataset built from historical offers and
their v1 evaluations. This file records the **first scored run as the baseline to
beat**: a later prompt or graph change should raise (or at least hold) every score.

## How to (re)generate

```bash
# 1. Build the dataset from SQLite (offers + v1 evaluations -> reference verdicts).
uv run python scripts/build_eval_dataset.py --user jorge

# 2. Run the subgraph over the dataset and write this file with the numbers.
uv run python scripts/run_eval.py --write-baseline
```

The dataset is also written to `data/evals/dataset.jsonl` (and pushed to a Langfuse
dataset when keys are present). Each run is saved to `data/evals/eval-<ts>.json`.

## Scores

Each score is the mean over the dataset, in `[0, 1]`.

| Score | Meaning |
| --- | --- |
| `verdict_agreement` | Graph verdict vs reference label (1.0 exact, 0.5 apply↔maybe near-miss, 0.0 otherwise) |
| `faithfulness` | Analysis/draft invents no company/offer facts beyond the offer + dossier (LLM judge, `gpt-4o`) |
| `specificity` | Draft cites ≥1 concrete company fact (scored only on drafted items) |

## Baseline numbers

> **Pending first live run.** The numbers are produced by `run_eval.py`, which makes
> live `gpt-4o`/`gpt-4o-mini` calls and (optionally) records to Langfuse. Per the
> constitution's key rule, the live run waits on real Azure/Langfuse keys. Run the
> two commands above to fill this table; `--write-baseline` overwrites this section
> automatically.

| Score | Baseline |
| --- | --- |
| `verdict_agreement` | _pending_ |
| `faithfulness` | _pending_ |
| `specificity` | _pending_ |
