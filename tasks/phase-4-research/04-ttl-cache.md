# Phase 4 · Task 04 — TTL cache for company research

## Objective
Avoid re-researching a company we already know about within 30 days. Simple, DB-backed.

## Acceptance criteria
- [ ] `CompanyResearcher.research(name)` first checks the `companies` table for an existing row with `expira_en > now()`. If found, returns the existing dossier without any search or LLM call.
- [ ] If expired or absent, runs the full research and writes back.
- [ ] TTL configurable via setting `COMPANY_RESEARCH_TTL_DAYS` (default 30).
- [ ] Optional CLI flag `--force-refresh` to bypass the cache.
- [ ] Cache hits / misses logged with structured fields (no PII).

## Files to create / modify
- `src/agents/company_researcher.py` (extend Task 03)
- `src/config.py` (add setting)

## Dependencies
- Phase 4 / Task 03

## Estimated effort
**S**

## Testing notes
Test: first call hits the LLM mock once, second call within TTL returns the same dossier without invoking the mock again. Force refresh re-runs.
