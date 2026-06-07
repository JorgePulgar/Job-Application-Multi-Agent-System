# Task plan — Job Application Multi-Agent System

Single source of truth for execution order. Work top-to-bottom. One git commit per task. After each task, STOP and ask the user to verify before proceeding.

**At the end of Phase 10, STOP. Phase 11 requires explicit user approval.**

---

## Phase 1 — Foundation

- [ ] [01 — Project scaffolding](phase-1-foundation/01-project-scaffolding.md)
- [ ] [02 — Env / config / logging](phase-1-foundation/02-env-config-logging.md)
- [ ] [03 — User profile Pydantic models](phase-1-foundation/03-user-profile-models.md)
- [ ] [04 — DB schema + Alembic initial migration (v1)](phase-1-foundation/04-db-schema-migrations.md)
- [ ] [05 — User YAML schema, examples, loader](phase-1-foundation/05-user-yaml-examples.md)
- [ ] [06 — CLI skeleton](phase-1-foundation/06-cli-skeleton.md)

## Phase 2 — Scraping

- [ ] [01 — Base scraper interface](phase-2-scraping/01-base-scraper-interface.md)
- [ ] [02 — JobOffer Pydantic model](phase-2-scraping/02-job-offer-model.md)
- [ ] [03 — Adzuna scraper](phase-2-scraping/03-adzuna-scraper.md)
- [ ] [04 — Jooble scraper](phase-2-scraping/04-jooble-scraper.md)
- [ ] [05 — Welcome to the Jungle scraper (Playwright)](phase-2-scraping/05-wttj-scraper.md)
- [ ] [06 — Deduplication service](phase-2-scraping/06-dedup-service.md)
- [ ] [07 — CLI: scrape](phase-2-scraping/07-cli-scrape.md)
- [ ] [08 — Scraping tests](phase-2-scraping/08-tests.md)

## Phase 3 — Filtering

- [ ] [01 — Azure OpenAI client wrapper](phase-3-filtering/01-azure-openai-client.md)
- [ ] [02 — OfferFilter agent](phase-3-filtering/02-offer-filter-agent.md)
- [ ] [03 — Spanish filter prompt with few-shot](phase-3-filtering/03-filter-prompt.md)
- [ ] [04 — CLI: filter](phase-3-filtering/04-cli-filter.md)
- [ ] [05 — Filter tests](phase-3-filtering/05-tests.md)

## Phase 4 — Company Research

- [ ] [01 — Web search service (Bing + DuckDuckGo fallback)](phase-4-research/01-web-search-service.md)
- [ ] [02 — CompanyDossier Pydantic model](phase-4-research/02-company-dossier-model.md)
- [ ] [03 — CompanyResearcher agent](phase-4-research/03-company-researcher-agent.md)
- [ ] [04 — TTL cache (30-day default)](phase-4-research/04-ttl-cache.md)
- [ ] [05 — CLI: research-companies](phase-4-research/05-cli-research.md)
- [ ] [06 — Research tests](phase-4-research/06-tests.md)

## Phase 5 — Evaluation

- [ ] [01 — ViabilityEvaluation Pydantic model](phase-5-evaluation/01-viability-evaluation-model.md)
- [ ] [02 — ViabilityEvaluator agent](phase-5-evaluation/02-viability-evaluator-agent.md)
- [ ] [03 — CLI: evaluate](phase-5-evaluation/03-cli-evaluate.md)
- [ ] [04 — Evaluation tests](phase-5-evaluation/04-tests.md)

## Phase 6 — Application Writing

- [ ] [01 — Draft Pydantic model](phase-6-writing/01-draft-model.md)
- [ ] [02 — ApplicationWriter agent](phase-6-writing/02-application-writer-agent.md)
- [ ] [03 — Writer prompt (Spanish, rules)](phase-6-writing/03-writer-prompt.md)
- [ ] [04 — Post-generation lint + regeneration](phase-6-writing/04-post-generation-lint.md)
- [ ] [05 — Save drafts to DB + markdown files](phase-6-writing/05-save-drafts.md)
- [ ] [06 — CLI: write-drafts](phase-6-writing/06-cli-write-drafts.md)
- [ ] [07 — Writer tests](phase-6-writing/07-tests.md)

## Phase 7 — Orchestration

- [ ] [01 — Orchestrator: chain scrape→filter→research→evaluate→write](phase-7-orchestration/01-orchestrator-chain.md)
- [ ] [02 — Per-offer error handling](phase-7-orchestration/02-error-handling.md)
- [ ] [03 — Run log persistence](phase-7-orchestration/03-run-log-persistence.md)
- [ ] [04 — Token / cost tracking](phase-7-orchestration/04-token-cost-tracking.md)
- [ ] [05 — CLI: orchestrator run](phase-7-orchestration/05-cli-orchestrator.md)

## Phase 8 — Dashboard (v1)

- [ ] [01 — FastAPI backend](phase-8-dashboard/01-fastapi-backend.md)
- [ ] [02 — Next.js scaffolding (shadcn, Tailwind, dark mode)](phase-8-dashboard/02-nextjs-scaffolding.md)
- [ ] [03 — `/` login picker](phase-8-dashboard/03-login-picker-page.md)
- [ ] [04 — `/drafts` list](phase-8-dashboard/04-drafts-list-page.md)
- [ ] [05 — `/drafts/[id]` detail + P.S. toggle](phase-8-dashboard/05-drafts-detail-page.md)
- [ ] [06 — `/history`](phase-8-dashboard/06-history-page.md)
- [ ] [07 — `/settings` (read-only YAML)](phase-8-dashboard/07-settings-page.md)
- [ ] [08 — Local dev setup docs](phase-8-dashboard/08-local-dev-docs.md)

## Phase 9 — Automation

- [ ] [01 — daily-run.yml workflow](phase-9-automation/01-daily-run-workflow.md)
- [ ] [02 — DB / drafts persistence strategy](phase-9-automation/02-db-persistence-strategy.md)
- [ ] [03 — Telegram notifier service + summary](phase-9-automation/03-telegram-notifier.md)
- [ ] [04 — Cost alert via Telegram](phase-9-automation/04-cost-alerts.md)

## Phase 10 — Polish & Docs

- [ ] [01 — Bilingual README + mermaid architecture diagram](phase-10-polish/01-bilingual-readme.md)
- [ ] [02 — docs/architecture.md](phase-10-polish/02-architecture-docs.md)
- [ ] [03 — Dashboard screenshots](phase-10-polish/03-dashboard-screenshots.md)
- [ ] [04 — Example runs](phase-10-polish/04-example-runs.md)
- [ ] [05 — Portfolio tag](phase-10-polish/05-portfolio-tag.md)

---

### ⛔ STOP after Phase 10

Phase 11 requires **explicit user approval** before starting. Do not begin Phase 11 task 1 without it.

---

## Phase 11 — Warm Outreach (v1.1, after explicit approval)

- [ ] [01 — Schema additions (outreach_targets, outreach_signals) + Alembic migration](phase-11-warm-outreach/01-schema-additions.md)
- [ ] [02 — PersonFinder agent](phase-11-warm-outreach/02-person-finder-agent.md)
- [ ] [03 — WarmMessageWriter agent](phase-11-warm-outreach/03-warm-message-writer-agent.md)
- [ ] [04 — Orchestrator integration + daily/weekly caps](phase-11-warm-outreach/04-orchestrator-integration.md)
- [ ] [05 — Dashboard outreach pages](phase-11-warm-outreach/05-dashboard-outreach-pages.md)
- [ ] [06 — Manual-context flow](phase-11-warm-outreach/06-manual-context-flow.md)
- [ ] [07 — Signal scanner service + weekly-signals.yml](phase-11-warm-outreach/07-signal-scanner-service.md)
- [ ] [08 — Telegram outreach summary + signal alerts](phase-11-warm-outreach/08-telegram-outreach-summary.md)

---

### ⛔ STOP after Phase 11

Phase 12 is **v2 scope** (multilingual + multi-country). Requires **explicit user approval** before starting, only after v1 (Phase 10) and v1.1 (Phase 11) are complete.

---

## Phase 12 — Multilingual & Multi-country (v2, after explicit approval)

Lifts the v1 "Spain + Spanish only" constraint: per-user target countries and Spanish+English search/drafting. The v1 "all prompts in Spanish" rule stays for v1/v1.1; Phase 12 / Task 04 introduces locale-aware prompts that override it for v2 only.

- [ ] [01 — Per-user target countries + search languages](phase-12-multilingual/01-config-countries-languages.md)
- [ ] [02 — Multi-country / multi-locale scrapers](phase-12-multilingual/02-multi-country-scrapers.md)
- [ ] [03 — Bilingual search keyword expansion](phase-12-multilingual/03-bilingual-search-keywords.md)
- [ ] [04 — Locale-aware prompt loader + English prompts](phase-12-multilingual/04-locale-aware-prompts.md)
- [ ] [05 — Draft language selection](phase-12-multilingual/05-draft-language-selection.md)
- [ ] [06 — Multilingual / multi-country tests](phase-12-multilingual/06-tests.md)

---

## Phase EXTRA — Public Repo Readiness (optional, off the main track)

**Not part of v1/v1.1/v2.** Repo stays **private for personal use** by default.
Run this phase ONLY if/when Jorge decides to make the repo public. Order matters:
the secret/PII audit (Task 01) is a hard gate before anything else, and the repo
must not be flipped public until it passes.

- [ ] [01 — Secret & PII audit before going public](phase-extra-public-repo/01-secret-pii-audit.md)
- [ ] [02 — LICENSE + repo metadata](phase-extra-public-repo/02-license-and-metadata.md)
- [ ] [03 — Public-facing README pass + badges](phase-extra-public-repo/03-public-readme-pass.md)
- [ ] [04 — GitHub Release v1.0.0](phase-extra-public-repo/04-github-release.md)
- [ ] [05 — Flip repo to public](phase-extra-public-repo/05-flip-public.md)
