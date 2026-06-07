# Phase EXTRA · Task 05 — Flip repo to public

> ⚠️ **EXTRA / OPTIONAL phase.** Irreversible-ish: once public + indexed, assume
> permanent. Run ONLY after Tasks 01-04 pass and Jorge gives explicit go-ahead.

## Objective
Change repository visibility to public.

## Acceptance criteria
- [ ] Task 01 (secret/PII audit) confirmed PASSED with zero findings.
- [ ] Jorge gives explicit "make it public" confirmation in chat.
- [ ] Settings → General → Danger Zone → Change visibility → Public.
- [ ] Re-verify after flip: repo page loads logged-out, raw screenshot URLs return
  200, release images render, no `config/users/*.yaml` / `.env` / `data/` exposed.
- [ ] Confirm GitHub Actions secrets are still set (visibility change does not leak
  them, but verify the daily-run workflow still has its secrets).

## Implementation notes
- This is a Jorge-performed UI action. The assistant must NOT flip visibility.
- If anything in the audit is stale, re-run Task 01 before flipping.

## Files to create / modify
- (None — GitHub setting)

## Dependencies
- Tasks 01-04

## Estimated effort
**S**

## Testing notes
Post-flip verification checklist above.
