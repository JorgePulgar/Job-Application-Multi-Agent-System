# Phase 10.5 · Task 00 — Constitution amendment + language decision (GATED)

## Objective
Make the LangGraph adoption an explicit, approved change to the constitution
before any code is written. This phase contradicts the current CLAUDE.md stack
(plain Python orchestrator, `openai` SDK, structlog, no LangGraph/Langfuse), so
the constitution must record the exception and its boundaries.

## Acceptance criteria
- [x] CLAUDE.md updated: a new subsection under §2 (Architecture) noting that the
      per-offer `research → eval → draft` slice runs as a **LangGraph subgraph**
      (`evaluate_and_draft`), while the rest of the pipeline stays plain Python.
- [x] CLAUDE.md §2 tech stack updated: add `langgraph` and `langfuse`; explicitly
      state **LangChain-classic LLM wrappers/chains are NOT used** (LangGraph-only).
- [x] CLAUDE.md updated: nodes call the existing `AzureOpenAIClient` +
      `prompt_loader`; prompt caching and structured outputs are preserved.
- [x] **Language rule recorded (DECIDED): match the offer's language** — English
      JD → English analysis + draft; Spanish JD → Spanish (README §7). Written into
      CLAUDE.md §4 as a per-subgraph exception to the global Spanish-only rule.
      `ParsedOffer.detected_language` drives it.
- [x] CLAUDE.md §8 (Scope) updated: this subgraph **does not** introduce a vector
      DB, a new Azure resource, or LangChain-classic; SQLite-only still holds
      (LangGraph checkpointer uses the existing SQLite).
- [x] Note that the subgraph supersedes `ViabilityEvaluator`/`ApplicationWriter`
      call-sites in the per-offer loop but the agents/code remain for reference and
      tests until Task 11 wires the replacement behind a feature flag.

> **Approved by Jorge 2026-06-10.** CLAUDE.md §2/§4/§8 amended in commit alongside
> this task. Phase unblocked — Task 01 may start.

## Files to create / modify
- `CLAUDE.md`

## Dependencies
- None. **This task gates the whole phase — must be approved before Task 01.**

## Estimated effort
**S**

## Testing notes
No code. After editing, STOP and get explicit user approval of the amendment and
the language decision before starting Task 01.
