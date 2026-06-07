# Phase EXTRA · Task 01 — Secret & PII audit before going public

> ⚠️ **EXTRA / OPTIONAL phase.** Not part of v1 or v1.1. Run only if/when Jorge
> decides to make the repo public. Repo stays **private** by default.

## Objective
Guarantee no secrets or personal data are exposed before the repo is ever made
public. This is the gate — nothing else in this phase runs until it passes.

## Acceptance criteria
- [ ] Confirm `.env`, `config/users/*.yaml` (non-`.example`), and `data/` are
  gitignored AND were never committed (`git log --all --full-history -- <path>`).
- [ ] Scan full git history for secrets (Azure keys, Adzuna/Jooble keys, Telegram
  token, Bing key) — e.g. `gitleaks detect` or `trufflehog filesystem .` over the
  whole history, not just the working tree.
- [ ] Confirm committed example drafts / screenshots contain only fictional data
  (no real company names, real emails, real phone numbers).
- [ ] If any secret/PII is found in history: scrub with `git filter-repo` (or BFG),
  rotate the leaked key, force-push, and re-verify. Document what was rotated.
- [ ] Verify no real names beyond what Jorge consents to publish (the brief uses
  `jorge` / `madalina` usernames — confirm OK to expose or anonymize).

## Implementation notes
- Treat history scan as mandatory: a deleted-but-committed secret is still public.
- Prefer `gitleaks` (fast, CI-friendly). Add a config to ignore `.example` files.

## Files to create / modify
- (Possibly) `.gitleaks.toml`
- Git history (only if scrubbing required)

## Dependencies
- None (must run FIRST in this phase)

## Estimated effort
**M**

## Testing notes
Run the scanner; expect zero findings before proceeding.
