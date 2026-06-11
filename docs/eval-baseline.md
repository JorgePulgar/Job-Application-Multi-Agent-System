# Eval baseline — `evaluate_and_draft` subgraph

Scored run of the Phase 10.5 subgraph against a dataset built from real
historical offers + their v1 evaluations. These are the numbers to beat: a
later prompt/graph change should raise (or hold) every score. Regenerate:

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

Run `eval-20260611T085745Z` over 9 item(s); 3 produced a shippable draft (rest flagged `needs_manual_context`).

## Per-offer breakdown

| Offer | Graph verdict | Reference | verdict | faithfulness | specificity |
| --- | --- | --- | --- | --- | --- |
| 16 | apply | maybe | 0.50 | 1.00 | — |
| 19 | apply | maybe | 0.50 | 1.00 | — |
| 37 | apply | apply | 1.00 | 0.50 | 1.00 |
| 44 | apply | maybe | 0.50 | 0.70 | 1.00 |
| 50 | maybe | maybe | 1.00 | 1.00 | — |
| 84 | apply | maybe | 0.50 | 1.00 | — |
| 85 | apply | maybe | 0.50 | 0.95 | 1.00 |
| 91 | apply | skip | 0.00 | 1.00 | — |
| 110 | maybe | maybe | 1.00 | 1.00 | — |

`specificity` is `—` when no draft was shipped (skip verdict or
`needs_manual_context`), so it does not enter that item's score.

## Observations

- The graph runs **more optimistic than v1**: 6 of 9 verdicts are `apply` where
  v1 said `maybe`, and one (`91`) is `apply` where v1 said `skip` — the single
  zero. This is the main drag on `verdict_agreement`; worth tuning the
  `assess_fit` rubric/score-bands before reading it as a regression.
- Faithfulness is high (0.906); the only real miss is offer `37` (0.50, one
  unsupported claim) — a target for the draft/assess prompts.
- Only 3 of 9 reached a shippable draft; the rest hit `needs_manual_context`
  (couldn't cite a concrete dossier fact), which is the specificity guard doing
  its job on thin dossiers rather than a scoring failure.

## Data provenance & known gaps

- Offers sourced from **Adzuna** only. **Jooble** is Cloudflare-WAF blocked
  (hard 403, key-independent) and **WTTJ** is not wired into the scrape
  runner, so neither contributes offers yet.
- Reference labels are the v1 `evaluations.recomendacion` mapped to
  apply/maybe/skip; they can be hand-corrected in `data/evals/dataset.jsonl`.
