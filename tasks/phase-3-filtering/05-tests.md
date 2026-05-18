# Phase 3 · Task 05 — Filter tests

## Objective
Tighten the test net around the filter pipeline.

## Acceptance criteria
- [ ] Unit test for `OfferFilter.evaluate`: relevant decision, discarded decision, red-flag short-circuit.
- [ ] Integration test for the CLI command using mocked LLM.
- [ ] Test that retries fire on a synthetic 429 from the LLM client (using the wrapper's retry).
- [ ] All tests run in < 5s and require no network.

## Files to create / modify
- `tests/unit/test_offer_filter.py` (extend)
- `tests/integration/test_filter_cli.py`

## Dependencies
- Phase 3 / Tasks 01-04

## Estimated effort
**S**

## Testing notes
Use a deterministic fake LLM response factory (`tests/utils/fake_llm.py`) so multiple tests share canned responses.

## End of Phase 3
After this task: tell the user "Phase 3 complete. Verify: scrape a small batch, then `python -m src.cli filter --user jorge --limit 5`. Approve to start Phase 4."
