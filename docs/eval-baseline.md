# Eval baseline — `evaluate_and_draft` subgraph

First scored run of the Phase 10.5 subgraph against the historical-offer
dataset. These are the numbers to beat: a later prompt/graph change should
raise (or hold) every score. Regenerate with:

```bash
uv run python scripts/build_eval_dataset.py --user jorge
uv run python scripts/run_eval.py --write-baseline
```

## Scores

Each score is the mean over the dataset, in `[0, 1]`.

| Score | Meaning | Baseline |
| --- | --- | --- |
| `verdict_agreement` | Graph verdict vs reference (1 exact, 0.5 near-miss) | 0.611 |
| `faithfulness` | No invented company/offer facts (LLM judge, gpt-4o) | 0.906 |
| `specificity` | Draft cites ≥1 concrete company fact (drafted items only) | 1.000 |

Run `eval-20260611T085745Z` over 9 item(s).
