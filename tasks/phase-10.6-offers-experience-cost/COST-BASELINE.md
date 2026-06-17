# Phase 10.6 · Task 08 — Cost baseline (`evaluate_and_draft` subgraph)

**Analysis only — no behavior changes.** This is the data contract for Task 09:
where per-offer LLM spend actually goes, so cuts target measured cost, not guesses.

## Provenance

- **Source run:** Langfuse session `eval-20260612T073850Z` — the most recent full
  eval run (9 offers, user `jorge`), the same run scored in
  `data/evals/eval-20260612T073850Z.json` (verdict_agreement 0.556, faithfulness
  0.922, specificity 1.0). Pulled via the Langfuse CLI; per-node cost/tokens come
  from generation observations attributed to their parent node span.
- **Cost unit:** USD, exactly as Langfuse computes from the Azure list prices.
  `usage_tracker.py` reports the same model at EUR ≈ USD × 0.92.
- **No new instrumentation.** Numbers trace to a named run. Two measurement gaps
  (research cold cost, pre/post-loop verdict delta) are logged below as Task 09
  prerequisites, not fixed here.

## Total

| Metric | Value |
| --- | --- |
| Graph LLM cost, 9 offers (excl. eval judge) | **$0.20002** |
| Graph cost / offer — mean / min / max | **$0.0222** / $0.0070 / $0.0309 |
| Eval faithfulness judge (gpt-4o, **not** the prod path) | $0.02726 (9 calls) |

The faithfulness judge runs inside the same trace but is an eval scorer, not a
production node — it is excluded from every graph number below.

## Cost & tokens per node (9 offers)

| Node | Model | LLM calls | Cost $ | % graph | Input tok | Cached tok | Output tok |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ingest_offer` | gpt-4o-mini | 9 | 0.00185 | 0.9% | 9 760 | 0 | 650 |
| `research_company` | gpt-4o¹ | **0** | **0.00000** | 0% | — | — | — |
| `extract_sponsorship` | gpt-4o-mini | 9 | 0.00133 | 0.7% | 7 494 | 0 | 338 |
| `match_profile` | gpt-4o | 9 | 0.03170 | 15.8% | 9 578 | **0** | 776 |
| `assess_fit` | gpt-4o | **24** | **0.08859** | **44.3%** | 40 885 | 33 152 | 2 782 |
| `gather_more` | (web search, no LLM) | 0 | 0.00000 | 0% | — | — | — |
| `human_review` | (interrupt, no LLM) | 0 | 0.00000 | 0% | — | — | — |
| `draft_cover_letter` | gpt-4o | **17** | **0.07654** | **38.3%** | 23 403 | 19 072 | 4 187 |
| **GRAPH TOTAL** | | 68 | **0.20002** | | | | |

¹ `research_company` made **zero** LLM calls in this run — every company was already
in the `companies` TTL cache (`CompanyResearcher` reuse). See the cold-run gap below.

**Two nodes are 82.6% of graph spend: `assess_fit` (44%) and `draft_cover_letter`
(38%).** Both are inflated by their respective loops (next sections).

## Confidence-loop (`gather_more`) cost

The loop is effectively the default path, not an exception:

| Offer | assess_fit calls | gather_more fires |
| --- | ---: | ---: |
| 16, 50, 85, 91, 110 | 3 | 2 (maxed) |
| 37, 44 | 3 | 2 (maxed) |
| 84 | 2 | 1 |
| 19 | 1 | 0 |

- **8 of 9 offers looped; `gather_more` fired 15 times across 9 offers** (cap is 2).
- `assess_fit` ran **24 times for 9 offers** — 15 of those calls (62%) are loop
  re-runs. At $0.00369/call that is **~$0.055 total ≈ $0.0061/offer** of pure loop
  overhead — about 28% of the entire graph cost.
- Offer 91 looped twice and then returned `skip` — three gpt-4o assessments to
  reach "no draft."
- `gather_more` itself is cheap (free/cheap web search, no LLM); the cost is the
  extra `assess_fit` gpt-4o pass each loop triggers.
- **`missing_info` is almost always non-empty**, so the loop is firing as the norm
  rather than for genuinely under-researched offers — the prime Task-09 question is
  whether the second pass ever changes the verdict (see gap #2).

## Draft regeneration cost

`draft_cover_letter` ran **17 times for 7 drafted offers** (skip offers 19, 91 ship
no draft). The regen cap is 3 attempts (prohibited-words + specificity gate):

| Attempts | Offers |
| --- | --- |
| 3 (maxed) | 16, 50, 85, 110 (+84) |
| 1 (clean) | 37, 44 |

- **5 of 7 drafts hit the 3-attempt ceiling.** ~10 of 17 calls are regenerations:
  ~$0.045 total ≈ **$0.0050/offer** of regen overhead.
- Regeneration is the norm, not the exception — the first-pass draft rarely clears
  the prohibited-words / specificity check.

## Prompt-cache effectiveness

CLAUDE.md §4 requires the stable system message + CV to be cached. Reality:

| Node | Cached / input | Hit | Note |
| --- | --- | --- | --- |
| `assess_fit` | 33 152 / 40 885 | **81%** | working as intended |
| `draft_cover_letter` | 19 072 / 23 403 | **81%** | working as intended |
| `match_profile` | 0 / 9 578 | **0% ⚠** | CV re-billed at full input price every call |
| `ingest_offer` (mini) | 0 / 9 760 | 0% | low impact (mini, ~$0.0002/offer) |
| `extract_sponsorship` (mini) | 0 / 7 494 | 0% | low impact (mini, ~$0.0001/offer) |

- **⚠ `match_profile` caches nothing despite `cacheable_system=True` and the CV in
  its system prompt.** Its cacheable prefix is ~1 064 tokens/call — at or under
  Azure's **1 024-token minimum** for prompt caching, so the cache never engages,
  while the larger-prefix `assess_fit`/`draft` nodes cache at 81%. The CV is paid at
  full gpt-4o input price on all 9 calls.
- The two mini nodes also miss cache but are negligible.

## Model-routing audit

| Node | Deployment | Verdict |
| --- | --- | --- |
| `ingest_offer` | gpt-4o-mini | ✓ correct (mechanical extraction) |
| `extract_sponsorship` | gpt-4o-mini | ✓ correct (mechanical extraction) |
| `match_profile` | gpt-4o | ⚠ candidate to downgrade (structured skill-mapping) |
| `assess_fit` | gpt-4o | ✓ reasoning — keep |
| `draft_cover_letter` | gpt-4o | ✓ writing — keep |
| `research_company` | gpt-4o¹ | ✓ synthesis — keep (cold path) |

No mechanical node is wrongly on gpt-4o except the borderline `match_profile`.

## Measurement gaps (Task-09 prerequisites)

1. **Research cost is unmeasured.** `research_company` hit the warm company cache on
   all 9 offers → $0 here. On a cold daily run it makes a gpt-4o + web-search
   synthesis call and is plausibly the single most expensive node. **The
   $0.0222/offer baseline understates a cold run.** Task 09 must measure one
   cache-cold run before claiming a research-node saving.
2. **Loop value is unmeasured.** We see the loop fires ~always and costs ~$0.006/
   offer, but not whether the post-loop `assess_fit` verdict ever differs from the
   pre-loop one. Task 09 needs that delta (cheap to capture: log verdict per pass)
   before trimming `MAX_LOOPS`.

## Ranked optimization candidates (input contract for Task 09)

Highest $/offer saving first. "Guard" = must not regress the eval baseline
(verdict_agreement 0.556, faithfulness 0.922, specificity 1.0).

1. **Trim the confidence loop — ~$0.003–0.006/offer (~14–28% of graph). FEASIBLE.**
   8/9 offers max the loop; it is the default, not the exception. Lower `MAX_LOOPS`
   2→1, and/or tighten the `missing_info` trigger so the loop fires only when a
   second pass can plausibly help. Guard with verdict_agreement (gap #2 first).

2. **Reduce draft regeneration — ~$0.004–0.005/offer (~20% of graph). FEASIBLE but
   quality-coupled.** 5/7 drafts hit the 3-attempt ceiling. Strengthen the draft
   prompt so the first pass clears prohibited-words + specificity. Guard with
   specificity (currently 1.0 — must hold) and the prohibited-words post-check.

3. **`match_profile` → gpt-4o-mini — ~$0.003/offer. RISKY-TO-QUALITY.** Cuts ~94%
   of a 15.8% node, but skill-matching feeds the verdict. Only with a clean
   verdict_agreement + faithfulness A/B showing no regression.

4. **Fix `match_profile` prompt caching — ~$0.001/offer. FEASIBLE, low saving.**
   Push the cacheable prefix above the 1 024-token floor (or fold `match_profile`
   into `assess_fit`, which already caches). Smallest win; do after 1–2.

**Stack rank if quality holds: loop trim → draft regen → match-profile model →
match-profile cache.** Address research cold cost (gap #1) as a measurement task
before any research-node change.
