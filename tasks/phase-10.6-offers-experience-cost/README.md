# Phase 10.6 — Offer visibility, experience filtering & cost optimization

> Slots **after** Phase 10.5 (LangGraph subgraph) and **before** Phase 11 (warm
> outreach, gated). Decimal insert — same pattern as 10.5. Does **not** renumber
> or touch Phases 11/12.

## 0. Status

**Not gated.** This phase introduces no constitution amendment, no new Azure
resource, no vector DB, and no LinkedIn scraping. It stays inside CLAUDE.md as
written: SQLite-only, prompts in `src/prompts/*.md`, LLM calls in
`src/services/`, full type hints + `mypy --strict` + `ruff`, one commit per task.

## 1. Why this exists

Product gaps surfaced after v1 + Phase 10.5:

1. **Per-user offer independence.** `offers.user_id` exists but a global
   `UniqueConstraint("hash_unico")` means the same public job can only be stored
   once across all users — the second user's identical offer is dropped on an
   `IntegrityError`. Offers must be independent per user (Jorge's queue ≠
   Madalina's). Fix = composite unique `(user_id, hash_unico)` + migration.
2. **Offer visibility (#4).** The dashboard only surfaces offers that reached a
   draft. A daily run scrapes 100+ offers; the user cannot see the
   `nueva` / `filtrada` / `descartada` ones. They want a per-user raw-offers view,
   independent of analysis state.
3. **Experience filtering (#3).** Scrapers search every target role with no
   seniority constraint. Add a per-profile `experience_level` (Jorge + Madalina
   are both **junior**) that narrows the *search* (`junior` ⇒ 0–2 years) via
   keywords + any native platform filter — at scrape time, before LLM spend.
4. **User-selectable search (#3 cont.).** Each user must choose *what kind of
   offers* they look for (roles, sectors, seniority, location, salary) **from the
   dashboard** (decided 2026-06-13), not only by hand-editing YAML. Needs a write
   API + an editable settings form; YAML stays the source of truth.
5. **Cost optimization (#1).** Phase 10.5 added Langfuse cost/latency tracing + an
   eval baseline. Use that data to cut spend per offer **without** regressing
   draft quality — measured, not blind.

## 2. Scope boundaries

- **No LinkedIn integration.** Rejected after review (direct guest-API scraping
  violates CLAUDE.md §8 + LinkedIn ToS; reconsider only as a web-search source in
  a later phase if ever). See conversation 2026-06-13.
- **No re-architecture into "specialized agents".** Already done in Phase 10.5
  (LangGraph nodes). LangChain-vs-LangGraph already decided: LangGraph-only.
- Offer-visibility work **extends** the FastAPI contract + dashboard with a new
  read-only per-user view; it does not change existing draft endpoints.
- Experience filtering changes the `UserProfile` model, both user YAMLs +
  examples, and the two scrapers (`adzuna`, `jooble`). No `wttj` scraper exists in
  `src/agents/job_scraper/` today, so only those two are in scope.
- User-selectable search adds **one write path** to profile YAML (an explicit,
  small editable allow-list: roles / sectors / experience_level / location /
  min_salary). YAML stays the single source of truth the scrapers load; the API
  read-modify-writes it atomically. CV / experiences are never editable here.
- Cost work targets the **active graph path** (`src/graph/`) + `AzureOpenAIClient`
  caching + `usage_tracker`. Guarded by the Phase 10.5 eval baseline so quality
  cannot silently regress.

## 3. Task list

- `01` — Per-user offer independence: composite unique `(user_id, hash_unico)` + migration
- `02` — API: list scraped offers per-user by `estado` (read-only) + per-state counts
- `03` — Dashboard: scraped-offers page incl. unanalyzed, estado filter, nav item
- `04` — `experience_level` on `UserProfile` + YAML + examples (both users `junior`)
- `05` — Scrapers filter by experience (Adzuna + Jooble keyword + native params)
- `06` — Search-config write API (PUT editable profile subset → YAML, validated)
- `07` — Settings page: editable search config (roles, sectors, seniority, location, salary)
- `08` — Cost baseline read from Langfuse (report: €/offer, €/node, cache-hit)
- `09` — Apply targeted cost cuts + re-measure against the eval baseline

## 4. Ordering rationale

`01` first — data-correctness prerequisite so per-user offers actually exist
independently before anything lists them. `02 → 03`: per-user offers view
(smallest risk, infra present — `Offer.user_id` + `ix_offers_estado`). `04 → 05`:
experience model + scraper filtering. `06 → 07`: the user-selectable search config
(write API, then editable UI). `08 → 09` last: cost work is data-driven and must
run after a baseline read; `09` only applies cuts `08` justifies and re-runs the
eval set to prove no quality regression.
