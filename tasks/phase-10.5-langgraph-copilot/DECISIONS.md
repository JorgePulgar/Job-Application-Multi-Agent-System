# Phase 10.5 — Decision log

Running record of the choices behind this phase and **why**. Source for the
public README's "design decisions" section later. Append new entries; don't
rewrite history — supersede with a dated note.

Format: `## D-NN — <decision>` · **Date** · **Status** · **Why** · **Alternatives rejected**.

---

## D-01 — Build the job-offer analyzer as a LangGraph subgraph inside this repo, not a separate app
**Date:** 2026-06-10 · **Status:** accepted

**Why.** The analyzer overlaps ~80% with the existing `viability_evaluator` +
`company_researcher` + `application_writer`. A second standalone product would
duplicate the brain and, per Jorge's own goal ("make something useful"), would
become shelf-ware — he'd use the automated daily pipeline, not a manual
paste-a-URL copilot. Embedding it in the real tool means it earns its keep daily
*and* serves as the CV artifact.

**Alternatives rejected.**
- *Separate standalone repo* — cleaner CV demo, but two repos share one brain →
  drift + maintenance for a tool that gets used once (at interviews).
- *Leave it as a Claude skill* — not deployable, not on CV, Claude-runtime-bound.

## D-02 — LangGraph only; NOT LangChain-classic
**Date:** 2026-06-10 · **Status:** accepted

**Why.** This pipeline is locked to Azure OpenAI, has no vector DB (constitution),
already gets clean structured output via the `openai` SDK, and loads its own
Spanish prompts. LangChain-classic's value props (provider-swap, prebuilt RAG,
output parsers) target problems we don't have, and its LLM wrappers make
`cache_control` placement awkward — a real regression against the mandated prompt
caching. LangGraph is the orchestration layer that fits (fan-out/fan-in, cycles,
`interrupt()`, checkpointer) and, being the same ecosystem, still earns the
"LangChain" CV line. Nodes keep calling the existing `AzureOpenAIClient`.

**Alternatives rejected.**
- *LangChain instead of LangGraph* — wrong tool for a stateful HITL agent; would
  regress caching and add unused weight.
- *LangGraph + LangChain LLM wrappers* — breaks caching for no benefit.

## D-03 — Scope is the eval→draft slice only, behind a feature flag
**Date:** 2026-06-10 · **Status:** accepted

**Why.** Scrapers, dedup, and the offer filter are linear I/O — a graph adds
ceremony, no benefit. The graph-shaped value (parallel research, confidence loop,
HITL, recovery) lives only in `research → eval → draft`. A flag (`use_langgraph_eval`,
default off) keeps v1 byte-for-byte intact while building, and persistence maps
back to the existing tables so the dashboard/API contract is untouched.

## D-04 — Phase 10.5, sequenced before Phase 11
**Date:** 2026-06-10 · **Status:** accepted

**Why.** The subgraph reworks the draft core; Phase 11 (warm outreach) also
produces drafts. Building the graph first lets Phase 11 drafting ride on it
instead of being built twice. The `10.5` label avoids renumbering the existing
`phase-11`/`phase-12` task files + memory (renumbering = churn).

## D-05 — Language: match the offer
**Date:** 2026-06-10 · **Status:** accepted (Jorge)

**Why.** The skill is English-first (Jorge's job search), the constitution is
Spanish-first (daily users include `madalina`, ES roles). Matching the offer
language satisfies both: English JD → English analysis + draft, Spanish JD →
Spanish. Detected once at ingest (`ParsedOffer.detected_language`) and threaded
through. Consequence: needs an **English** banned-cliché list alongside the v1
Spanish one (the v1 prohibited-words list is Spanish-only).

**Alternatives rejected.** Spanish-only (loses Jorge's EN search); English-only
(wrong for ES roles + madalina); analyze-EN/draft-ES (mismatched, confusing).

## D-06 — Langfuse for tracing + eval
**Date:** 2026-06-10 · **Status:** accepted (Jorge wants proper tracking)

**Why.** The graph makes many LLM calls per run; "I instrument and evaluate my
agents" is a stronger CV line than "I built one." Task 09 = one trace per
application, per-node spans, cost/latency/tokens. Task 10 = eval dataset from past
offers + faithfulness/verdict/specificity scores to prove improvement across
versions. Attaches via LangGraph callbacks (not LangChain), so caching is intact.
No-op when keys absent, so the graph runs without Langfuse configured.

## D-07 — Constitution amendment approved
**Date:** 2026-06-10 · **Status:** accepted (Jorge)

**Why.** CLAUDE.md fixed the stack as plain-Python/openai-SDK/structlog with no
LangGraph/Langfuse. Adding them is a deliberate, recorded exception (CLAUDE.md
§2/§4/§8), not a silent drift. Task 00 done; phase unblocked.

---

### Open / to revisit
- **Python 3.14 compat** (venv is 3.14): confirm `langgraph`/`langfuse` support in
  Task 01 before pinning; fall back to a supported interpreter/version if not.
- ~~**Checkpointer DB location:** existing `state.db` vs a dedicated
  `graph_checkpoints.db` — decide in Task 07.~~ **RESOLVED (Task 07):** dedicated
  `data/graph_checkpoints.db` via `AsyncSqliteSaver`, kept separate from `state.db`
  so langgraph's internal checkpoint tables never collide with the app schema.
- **Score vs fit_level:** keep numeric `score` (0-100) alongside the skill's
  STRONG/MODERATE/WEAK `fit_level`; reconcile in Task 02.
