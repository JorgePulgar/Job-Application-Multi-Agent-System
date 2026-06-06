# Phase 10 · Task 04 — Example runs

## Objective
Save anonymized examples of generated drafts so visitors can see actual output quality without compromising privacy.

## Acceptance criteria
- [x] `docs/examples/` contains 2-3 example draft markdown files. Companies replaced with realistic but fictional names; user identity scrubbed.
- [x] One example must demonstrate a `needs_manual_context` flag with clear reasoning.
- [x] README links to these.

## Implementation notes
- 3 examples: 2 full drafts (NeuralForge ML Engineer, Helios Health Data Scientist) + 1 `needs_manual_context` with explicit reasoning (no verifiable company hook after 2 attempts).
- Draft content follows the voice rules: Spanish, proof-first, no em/en-dashes (verified), no banned vocab; identity scrubbed to `[…]` placeholders. Linked from both READMEs.

## Files to create / modify
- `docs/examples/*.md`
- `README.md` (link section)

## Dependencies
- Phase 6 / Task 05

## Estimated effort
**S**

## Testing notes
Manual review for PII leakage. Names of real recruiters, real companies you've applied to, etc. must be replaced.
