# Phase 4 · Task 06 — Research tests

## Objective
Phase-closing test sweep for company research.

## Acceptance criteria
- [x] Unit tests for `CompanyResearcher.research` covering: fresh research, cache hit, expired cache, force refresh.
- [x] Integration test for the CLI.
- [x] Test verifies no PII slips into any logged structured fields.

## Files to create / modify
- `tests/unit/test_company_researcher.py` (extend)
- `tests/integration/test_research_cli.py`

## Dependencies
- Phase 4 / Tasks 01-05

## Estimated effort
**S**

## Testing notes
Make sure mocked search results contain realistic-looking URLs and titles so the prompt-rendering path is exercised.

## End of Phase 4
After this task: tell the user "Phase 4 complete. Approve to start Phase 5."
