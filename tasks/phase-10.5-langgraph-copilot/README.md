# Phase 10.5 — LangGraph Evaluation+Draft Subgraph ("copilot")

> Slots **after** the tagged v1 (phase 10) and **before** Phase 11 (warm outreach).
> Rationale for ordering: this phase reworks the eval→draft core. Phase 11 also
> produces drafts; building the graph first means Phase 11 drafting rides on it
> instead of being built twice.

## 0. Status

**GATED.** This phase **amends the constitution** (CLAUDE.md fixes the stack as a
plain Python orchestrator with the `openai` SDK + structlog; it does not include
LangGraph/Langfuse). Task 00 makes that amendment explicit and must be approved
before any code task starts. Do not begin Task 01 until Task 00 is approved.

## 1. Why this exists

Two goals at once:

1. **Product:** replace the linear `research → eval → draft` slice with a graph
   that does parallel research, a confidence loop on borderline offers, real
   human-in-the-loop review, and checkpoint recovery for the unattended daily
   cron. Genuinely better drafts + a resumable pipeline.
2. **CV:** a deployable, **instrumented (Langfuse)** and **evaluated** agentic
   subgraph that exercises LangGraph fan-out/fan-in, conditional cycles,
   `interrupt()` human-in-the-loop, and a checkpointer — on a problem the author
   can speak to with conviction. Closes the named LangGraph/LangChain-ecosystem
   gap.

The source spec for the brain is the `job-offer-analyzer` Claude skill
(`.claude/skills/job-offer-analyzer.skill`). This phase turns that prompt into a
structured, deployed graph.

## 2. Scope boundaries

- **LangGraph only** for orchestration. **Do NOT adopt LangChain-classic LLM
  wrappers / chains / output parsers** — they fight prompt caching and the
  existing `openai`-SDK structured-output path. Nodes keep calling the existing
  `AzureOpenAIClient` + `prompt_loader` directly. (Using LangGraph already earns
  the "LangChain ecosystem" CV line.)
- Replaces the **call-sites** of `ViabilityEvaluator` + `ApplicationWriter` in
  the per-offer loop. Does **not** touch scrapers, dedup, the `OfferFilter`, the
  DB schema, the dashboard contract, or Telegram.
- Reuses existing `CompanyResearcher`, `CompanyDossier`, and the user `YAML`
  profiles. No new Azure resources.

## 3. The subgraph: `evaluate_and_draft`

```
                          ┌──────────────────────┐
        offer (DB row) ──►│   ingest_offer       │  mini → ParsedOffer
        + user_profile    └──────────┬───────────┘
                                     │  fan-out (Send)
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
     ┌────────────────┐   ┌────────────────────┐   ┌──────────────────┐
     │ research_company│  │ extract_sponsorship │  │  match_profile   │
     │ 4o + web (reuse)│  │ mini → Sponsorship  │  │ 4o → Requirement │
     │ → CompanyDossier│  │ Signal              │  │ Match            │
     └────────┬────────┘  └─────────┬──────────┘   └────────┬─────────┘
              └──────────────────────┼──────────────────────┘
                                     ▼  fan-in
                          ┌──────────────────────┐
                          │     assess_fit       │  4o → FitAssessment
                          └──────────┬───────────┘
                                     ▼
                          ◇ route_on_confidence ◇
              SKIP ───────┤                      ├─────── borderline & loops<2
               │          │                      │              │
               ▼          │                      │              ▼
             (END)        │                      │      ┌──────────────┐
                          │                      │      │ gather_more  │ re-research
                          │                      │      └──────┬───────┘
                          │   confident          │             │ back to
                          ▼                      ◄─────────────┘ assess_fit
                ┌──────────────────────┐
                │   human_review       │  interrupt()  → APPLY / MAYBE / SKIP
                │  (dashboard HITL)    │  + which-angle / clarifications
                └──────────┬───────────┘
                           ▼  approved APPLY/MAYBE
                ┌──────────────────────┐
                │  draft_cover_letter  │  4o → CoverLetterDraft (proof-first +
                └──────────┬───────────┘  prohibited-words post-check, max 2 regen)
                           ▼
                         (END)
```

**Checkpointer:** `SqliteSaver` (async variant) keyed by `(user, offer_id)` so a
paused `interrupt()` survives a process restart — the daily GitHub Actions run can
die mid-pipeline and resume.

## 4. State (`src/graph/state.py`)

`EvaluateDraftState` (TypedDict, `total=False`):

| key | type | set by |
|---|---|---|
| `offer_id` | `int` | caller |
| `username` | `str` | caller |
| `parsed` | `ParsedOffer` | ingest_offer |
| `dossier` | `CompanyDossier` | research_company (reused) |
| `sponsorship` | `SponsorshipSignal` | extract_sponsorship |
| `requirements` | `RequirementMatch` | match_profile |
| `fit` | `FitAssessment` | assess_fit |
| `loop_count` | `int` | route_on_confidence |
| `human_decision` | `HumanDecision \| None` | human_review (interrupt) |
| `draft` | `CoverLetterDraft \| None` | draft_cover_letter |

Reducers: branch outputs write disjoint keys, so no custom merge needed beyond the
fan-in node reading all three.

## 5. New Pydantic schemas (`src/models/fit.py`)

```python
class ParsedOffer(BaseModel):
    title: str
    detected_language: Literal["es", "en"]  # drives analysis + draft language
    seniority: str | None          # "junior" | "mid" | "senior" | None=not stated
    company: str
    sector: str | None
    location: str | None
    remote_policy: str | None      # remote / hybrid / onsite / not stated
    required_skills: list[str]
    preferred_skills: list[str]
    salary_raw: str | None
    languages: list[str]
    contract_type: str | None
    sponsorship_mention: str | None

class SponsorshipSignal(BaseModel):
    needs_sponsorship: bool | None  # None = cannot tell
    sponsorship_offered: bool | None
    geo_viable_for_spain: bool      # remote-EU or relocation possible?
    working_language: str | None
    blocker: str | None             # decisive blocker text, else None

RequirementStatus = Literal["met", "partial", "missing"]

class RequirementItem(BaseModel):
    requirement: str
    status: RequirementStatus
    note: str

class RequirementMatch(BaseModel):
    items: list[RequirementItem]
    standout_points: list[str]      # where the user stands out for THIS role
    gaps: list[str]

FitLevel = Literal["strong", "moderate", "weak"]
Recommendation = Literal["apply", "maybe", "skip"]

class TailoringPointers(BaseModel):
    cv_emphasis: list[str]
    cover_letter_hook: str
    gap_to_address: str | None

class FitAssessment(BaseModel):
    fit_level: FitLevel
    recommendation: Recommendation
    score: int = Field(ge=0, le=100)
    reasoning: str                  # 1-2 sentences, the decisive reason
    red_flags: list[str]
    missing_info: list[str]         # drives the confidence loop
    tailoring: TailoringPointers | None  # only when apply/maybe

class HumanDecision(BaseModel):
    decision: Recommendation        # user override of recommendation
    lead_angle: str | None
    clarifications: dict[str, str]  # answers to interrupt questions

class CoverLetterDraft(BaseModel):
    subject: str
    body: str
    lead_angle: str
    hook: str
```

`FitAssessment` supersedes the v1 `ViabilityEvaluation` for the graph path; the
mapping to the existing `evaluations` DB row is handled in the integration task
(persist `score`, `recommendation→estado`, `reasoning`).

## 6. Decision rubric (encoded into `assess_fit` system prompt)

From the skill's Notes — this is the calibration that makes verdicts honest:

- **Hard SKIP blockers only:** no right to work / sponsorship needed when not
  offered; geo-lock excluding Spain; required language the user lacks; "junior"
  role demanding 4+ years (stealth-senior).
- **Soft gaps (NEVER a SKIP alone):** missing bachelor's degree; 1-2 years
  experience asked. Note as gap / possible ATS risk, verdict stays APPLY/MAYBE.
- **Do not invent missing fields** → push them to `missing_info`, which can
  trigger one confidence-loop pass before weighing them as red flags.
- **SKIP is short:** route ends the graph; no draft, no tailoring.

## 7. Language rule (RESOLVED)

**Match the offer's language.** `ingest_offer` detects the offer language into
`ParsedOffer.detected_language` (`es`/`en`); every downstream node (sponsorship,
match, assess_fit, draft) produces its analysis and the final draft in that
language. English JD → English analysis + English draft; Spanish JD → Spanish.

This supersedes the global Spanish-only rule in CLAUDE.md §4 **for this subgraph
only** — record the exception in Task 00. Prompt templates that emit user-facing
text take the target language as a parameter rather than being hardcoded.

## 8. Compatibility risk

The venv is on **Python 3.14**. Confirm `langgraph` + `langfuse` support 3.14 in
Task 01 before committing the deps; if not, pin a working interpreter or version.

## 9. Task list

- `00` — constitution amendment + language decision **(GATED, approve first)**
- `01` — deps + graph package scaffold + state
- `02` — Pydantic fit schemas
- `03` — `ingest_offer` node
- `04` — research fan-out (company / sponsorship / profile-match)
- `05` — `assess_fit` fan-in node + rubric prompt
- `06` — confidence routing + `gather_more` loop (max 2)
- `07` — `human_review` interrupt + SqliteSaver checkpointer
- `08` — `draft_cover_letter` node (proof-first + prohibited-words post-check)
- `09` — Langfuse tracing (cost/latency per node + per application)
- `10` — eval dataset from past offers + faithfulness/quality scores
- `11` — orchestrator integration (feature-flagged) + DB persistence mapping
- `12` — tests (graph unit + mocked integration)
