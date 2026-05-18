# Phase 4 · Task 03 — CompanyResearcher agent

## Objective
Given a company name, gather public info via web search and synthesize a `CompanyDossier` with `gpt-4o`.

## Acceptance criteria
- [ ] `src/agents/company_researcher.py` implements `class CompanyResearcher` with `async def research(self, company_name: str) -> CompanyDossier`.
- [ ] Issues 3-5 web search queries: `"{name} empresa"`, `"{name} site:linkedin.com/company"`, `"{name} reseñas glassdoor"`, `"{name} stack tecnológico"`, `"{name} news"`.
- [ ] Pipes top results' titles + snippets into the LLM prompt (NOT the full pages — keep token use down).
- [ ] Uses structured outputs to return a `CompanyDossier`.
- [ ] Prompt files in `src/prompts/company_researcher.{system,user}.md` (Spanish).
- [ ] Persists/updates the `companies` row (`dossier_completo` JSON, `fecha_research`, `expira_en` = +30 days).

## Files to create / modify
- `src/agents/company_researcher.py`
- `src/prompts/company_researcher.system.md`
- `src/prompts/company_researcher.user.md`
- `tests/unit/test_company_researcher.py`

## Dependencies
- Phase 3 / Task 01
- Phase 4 / Tasks 01, 02

## Estimated effort
**L**

## Testing notes
Mock `search_web` and `AzureOpenAIClient.chat`. Verify: queries issued, prompt populated correctly, DB row upserted, expiration set 30 days out.
