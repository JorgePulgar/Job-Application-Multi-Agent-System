# Phase 11 · Task 02 — PersonFinder agent

## Objective
Given a company already researched in v1 + a target role profile, find 1-3 ranked AI/ML lead candidates using public web search ONLY. NEVER scrapes LinkedIn.

## Acceptance criteria
- [ ] `src/agents/person_finder.py` implements `class PersonFinder` with `async def find(self, company: db.Company, profile: UserProfile) -> list[OutreachCandidate]`.
- [ ] `OutreachCandidate` Pydantic model: `nombre`, `rol`, `linkedin_url` (HttpUrl, optional), `razon_eleccion`, `fuente_descubrimiento`.
- [ ] Search queries (configurable list, defaults below — all use the existing `search_web` service):
  - `"{empresa}" "AI engineer" site:linkedin.com/in`
  - `"{empresa}" "ML lead" site:linkedin.com/in`
  - `"{empresa}" "head of data" site:linkedin.com/in`
  - `"{empresa}" "CTO" site:linkedin.com/in`
  - `"{empresa}" engineering team site:{empresa-domain}`
- [ ] LLM (`gpt-4o`) processes the result list with structured outputs → ranked candidates.
- [ ] No HTTP request ever issued directly to `linkedin.com`. Enforce in code (assertion + a unit test).
- [ ] Persists candidates as `outreach_targets` rows with `estado='draft'`, links to `company_id`.
- [ ] Hard cap: max 3 candidates per company per run.

## Files to create / modify
- `src/agents/person_finder.py`
- `src/models/outreach.py` (extend with `OutreachCandidate`)
- `src/prompts/person_finder.{system,user}.md`
- `tests/unit/test_person_finder.py`

## Dependencies
- Phase 11 / Task 01

## Estimated effort
**M**

## Testing notes
Mock `search_web`. Test that no HTTP client is ever called with a `linkedin.com` host (use a spy on the http service). Test ranking output shape.
