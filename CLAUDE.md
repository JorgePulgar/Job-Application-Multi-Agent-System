# CLAUDE.md — Job Application Multi-Agent System

This file is the source of truth for how Claude must work on this repository. Read it at the start of every session.

---

## 1. Product summary

Multi-agent system that automates job hunting for two end users (Jorge and his partner) targeting AI / data / engineering roles in Spain. Runs daily, scans job platforms, evaluates each opportunity, generates personalized application drafts in Spanish (email + cover letter), and surfaces them in a Next.js dashboard for human review.

**Critical principle — human-in-the-loop.** The system NEVER sends anything automatically. It prepares drafts. The user reviews, edits, and decides.

**Scope:**
- **v1 (Phases 1-10)** — Flow B: responding to published job offers.
- **v1.1 (Phase 11)** — Warm LinkedIn outreach to AI/ML leads at companies already researched during Flow B. Built on top of v1.
- **OUT OF SCOPE entirely** — Flow A (cold outreach to companies without a posted offer). Do not build it. Do not stub it. Do not add hooks for it.

---

## 2. Architecture summary

Plain Python orchestrator + specialized agents, SQLite for state, GitHub Actions for scheduling, Next.js dashboard on Vercel with a small FastAPI backend reading the SQLite DB, Telegram for daily run summaries.

**Components (v1):**

- **Orchestrator** — entry point. Iterates users, runs the pipeline per user.
- **Job scraper agents** — one per platform (Adzuna, Jooble, Welcome to the Jungle). Common interface.
- **Offer filter agent** — `gpt-4o-mini`, relevant vs discard.
- **Company researcher agent** — `gpt-4o` + web search, produces structured company dossier.
- **Viability evaluator agent** — `gpt-4o`, score + pros/cons + recommendation.
- **Application writer agent** — `gpt-4o`, subject + email body + cover letter.
- **Database layer** — SQLAlchemy 2.x + SQLite + Alembic.
- **Dashboard** — Next.js 14 App Router + TS + Tailwind + shadcn/ui, dark mode default, mobile-friendly.
- **API** — small FastAPI app reading the SQLite DB.
- **Scheduler** — GitHub Actions cron workflow.
- **Notifications** — Telegram bot summary at end of each daily run.

**Component added in Phase 10.5 (LangGraph subgraph):**

- **`evaluate_and_draft` subgraph** — the per-offer `research → eval → draft` slice runs as a **LangGraph** subgraph (parallel research fan-out, a confidence loop, `interrupt()` human-in-the-loop, and a SQLite checkpointer for crash-resumable daily runs). The rest of the pipeline (scrapers, dedup, offer filter, orchestrator loop) stays plain Python. **LangGraph only — no LangChain-classic LLM wrappers/chains/parsers**; nodes call the existing `AzureOpenAIClient` + `prompt_loader`, preserving prompt caching and structured outputs. Supersedes the `ViabilityEvaluator`/`ApplicationWriter` call-sites behind a feature flag; those agents remain for reference/tests. See `tasks/phase-10.5-langgraph-copilot/`.

**Components added in v1.1 (Phase 11):**

- **Person finder agent** — finds AI/ML leads at researched companies via public web search (NEVER scrapes LinkedIn).
- **Warm message writer agent** — short Spanish outreach messages.
- **Signal scanner** — weekly job re-checking saved targets for new public activity.

**Tech stack (exact):**

- Python 3.11+, package manager `uv`
- `openai` SDK against Azure OpenAI
- Web search: Bing Search v7 if available, else `duckduckgo-search` fallback (detect at runtime)
- Scraping: `httpx` + `beautifulsoup4` for simple sites, `playwright` (async) for JS-heavy
- DB: `sqlalchemy` 2.x + SQLite + Alembic
- Models: `pydantic` v2
- Logging: `structlog`. CLI: `click`. Config: `pyyaml` + `python-dotenv`
- Dedup: `rapidfuzz`
- Tests: `pytest` + `pytest-asyncio` + `respx`
- Type check: `mypy --strict`. Lint/format: `ruff`
- **Phase 10.5 only:** `langgraph` (subgraph orchestration + SQLite checkpointer) and `langfuse` (tracing + eval). **NOT** LangChain-classic — LangGraph is used standalone; nodes keep calling the `openai`-SDK-based `AzureOpenAIClient`. (Confirm 3.14 support before pinning.)

**Dashboard stack:** Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui, deployed to Vercel.

---

## 3. Users

Two users — separate YAML profiles under `config/users/{username}.yaml`, validated via Pydantic v2 models. Shared infrastructure, separate filters and drafts.

Each profile contains: personal info, target roles, target sectors, tech stack, languages, minimum salary, location preference, red flags (auto-discard patterns), CV summary (markdown), experiences, education, certifications.

---

## 4. LLM strategy

Two Azure OpenAI deployments:

- `gpt-4o-mini` — cheap/mechanical: offer filter (relevant yes/no), structured extraction, dedup decisions, classifications.
- `gpt-4o` — reasoning/writing: company research synthesis, viability evaluation, email/cover letter, warm outreach.

**Prompt caching MUST be enabled** wherever supported. The user CV and stable system messages are cached.

**All prompts in Spanish.** Loaded from `src/prompts/*.md` at runtime — never hardcoded inline.

**Exception — Phase 10.5 `evaluate_and_draft` subgraph: match the offer's language.** The subgraph detects the offer language at ingest (`ParsedOffer.detected_language`) and emits its analysis and the final draft in that language — English JD → English, Spanish JD → Spanish. Prompts that produce user-facing text take the target language as a parameter. A per-language prohibited-words list applies (the v1 Spanish list plus an English banned-cliché equivalent).

### Prohibited words/phrases in drafts

Enforced via prompt and a post-generation check. Max 2 regeneration attempts; if still failing, mark draft as `needs_manual_context`.

- `apasionado/a`
- `proactivo/a`
- `jugador de equipo`
- `orientado a resultados`
- For warm outreach openers specifically: `espero que estés bien`, `vi tu perfil`, `estoy buscando oportunidades`
- Any generic corporate cliché

### Disclosure rule

Drafts NEVER disclose AI assistance in the email/message body. The user can choose, per draft from the dashboard, to append a P.S. mentioning the agent system. The agent never adds it by default.

### Specificity rule

Drafts must reference at least one concrete fact about the company (for applications) or about the recipient's work (for warm outreach). If no specific hook can be found, mark the draft as `needs_manual_context` rather than producing a generic message.

---

## 5. Azure resources

The **user** creates these manually. Do NOT use Azure SDKs to provision anything. Consume them via env vars only.

Required:
1. **Azure OpenAI resource** with deployments named `gpt-4o-mini` and `gpt-4o`.
2. **Bing Search v7** tier F1 (free). If unavailable, code falls back to DuckDuckGo at runtime.

No AI Search, no Storage Account, no Cosmos DB, no Functions, no App Service.

If a key the user hasn't provided is required, **STOP and ask explicitly**: "I need you to register at X and paste the key into .env. Tell me when done."

### Env vars (full list, committed to `.env.example`)

`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_API_VERSION` (default `2024-10-21`), `AZURE_OPENAI_DEPLOYMENT_MINI` (default `gpt-4o-mini`), `AZURE_OPENAI_DEPLOYMENT_4O` (default `gpt-4o`), `BING_SEARCH_KEY`, `BING_SEARCH_ENDPOINT` (default `https://api.bing.microsoft.com/v7.0/search`), `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `JOOBLE_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

---

## 6. Database (SQLite via SQLAlchemy 2.x + Alembic)

See `tasks/phase-1-foundation/04-db-schema-migrations.md` and `tasks/phase-11-warm-outreach/01-schema-additions.md` for full column definitions.

**v1 tables:** `users`, `companies`, `offers`, `evaluations`, `drafts`, `applications`, `run_logs`.

**v1.1 additions:** `outreach_targets`, `outreach_signals`.

Hash for `offers.hash_unico` = sha256 of normalized `titulo + empresa + ubicacion`. Near-duplicate detection inside the same scrape run uses `rapidfuzz`.

---

## 7. Project structure

```
job-agent/
├── CLAUDE.md
├── README.md / README.en.md
├── .env.example
├── pyproject.toml                  # uv
├── alembic.ini  /  alembic/versions/
├── tasks/                          # source of truth for execution
├── config/
│   ├── users/                      # gitignored except *.example
│   └── sources.yaml
├── src/
│   ├── orchestrator.py  /  cli.py  /  config.py  /  logging_setup.py
│   ├── models/                     # Pydantic
│   ├── db/                         # SQLAlchemy
│   ├── agents/
│   │   ├── job_scraper/{adzuna,jooble,wttj}.py
│   │   ├── offer_filter.py
│   │   ├── company_researcher.py
│   │   ├── viability_evaluator.py
│   │   ├── application_writer.py
│   │   ├── person_finder.py            # Phase 11
│   │   └── warm_message_writer.py      # Phase 11
│   ├── services/
│   │   ├── azure_openai.py
│   │   ├── web_search.py
│   │   ├── telegram.py
│   │   ├── dedup.py
│   │   └── signal_scanner.py           # Phase 11
│   └── prompts/                    # Spanish .md prompt templates
├── api/                            # FastAPI for dashboard
├── dashboard/                      # Next.js
├── tests/{unit,integration}/
├── data/{state.db,drafts/}         # runtime
└── .github/workflows/
    ├── daily-run.yml
    └── weekly-signals.yml          # Phase 11
```

---

## 8. Rules (non-negotiable)

### Workflow

- Work **phase by phase, task by task**, in the order defined in `tasks/`.
- **One git commit per task.** Format: `feat(phase-N): <task name>` (or `fix`, `test`, `docs`, `chore`).
- Before starting each task, **read its file and restate the acceptance criteria**.
- After finishing each task, **mark every acceptance-criteria checkbox as `- [x]`** in the task file, then **STOP and tell the user what to verify** before continuing.
- At the start of each session, **check which task files still have `- [ ]` checkboxes** to determine where to resume — do not rely on memory alone.
- Never skip or combine tasks without explicit approval.
- **At the end of Phase 10, STOP** and wait for explicit approval before Phase 11.

### Code quality

- Python 3.11+, full type hints. `mypy --strict` must pass.
- `ruff` lint and format before every commit.
- All public functions/classes documented with Google-style docstrings.
- No silent exception handling. Log and re-raise, or log and mark state as `error`.
- All HTTP and LLM calls live in `src/services/`, never inline in agents.
- All prompts in `src/prompts/*.md`, loaded at runtime, never inline strings.

### LLM

- `gpt-4o-mini` for cheap/mechanical, `gpt-4o` for reasoning/writing.
- Always enable prompt caching for stable system messages and the user CV.
- All prompts in Spanish.
- Enforce prohibited-words list via prompt + post-check. Max 2 regen attempts.
- Enforce specificity rule. If unmet after 2 attempts, mark as `needs_manual_context`.
- NEVER disclose AI assistance in draft body. Transparency P.S. is user-triggered, not default.

### Data

- SQLite only for v1 and v1.1. No vector DB. No external DB.
- All Pydantic models v2.
- **No PII in logs.** Mask emails and phones in log output.

### Testing

- Every agent has at least one unit test with mocked LLM/HTTP.
- Every scraper has at least one test with mocked response.
- Integration test for the full pipeline against mocked services.
- Tests must pass before each commit (pre-commit hook).

### Decisions

- If a library API is unfamiliar, **look it up before using**. Do NOT invent methods.
- If a technical decision has reasonable alternatives, **propose 2 and ask**. Don't decide alone on architecture-level choices.
- If a key/resource isn't provided, **STOP and ask explicitly**.
- Never write code that violates platform ToS. Respect robots.txt, rate-limit, no aggressive scraping.
- **NEVER scrape LinkedIn directly** under any circumstances. Use public web search results only.

### Scope

- Flow A is OUT OF SCOPE entirely. Do not stub. Do not add hooks for it.
- Dashboard auth: not in v1 or v1.1. User picker is sufficient.
- No multi-tenancy beyond 2 hardcoded users.
- Phase 11 only after Phase 10 is explicitly approved.
- **Phase 10.5 (LangGraph subgraph)** introduces no vector DB, no new Azure resource, and no LangChain-classic. SQLite-only still holds — the LangGraph checkpointer uses SQLite. Phase 10.5 runs before Phase 11. (Approved 2026-06-10.)

### Volume (Phase 11)

- Max **2 new outreach drafts per user per day**.
- Max **10 outreach drafts per user per week** (configurable; default is firm).
- Signal scanner runs **weekly**, not daily.

---

## 9. Commit message format

```
<type>(phase-N): <task name>
```

Where `<type>` is one of `feat`, `fix`, `test`, `docs`, `chore`, `refactor`. `N` is the phase number. The task name is short, lowercase, kebab-case-ish.

Example: `feat(phase-2): adzuna scraper`.

The bootstrap commit is the only one without a phase tag: `chore: bootstrap project structure and task plan`.

---

## 10. Definition of done per task

A task is "done" only when ALL of:

1. Code matches the acceptance criteria in the task file.
2. Tests pass (`pytest`).
3. `ruff check` and `ruff format --check` pass.
4. `mypy --strict src/` passes for any code touched.
5. The change is committed with the right message format.
6. The user has been told what to verify and approves moving on.
