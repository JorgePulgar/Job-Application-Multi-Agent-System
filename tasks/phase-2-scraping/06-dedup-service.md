# Phase 2 · Task 06 — Deduplication service

## Objective
Detect near-duplicate offers within a single scrape run and across the existing DB to avoid wasting LLM tokens on the same job twice.

## Acceptance criteria
- [x] `src/services/dedup.py` exposes:
  - `dedup_within_run(offers: list[JobOffer]) -> list[JobOffer]` — uses `hash_unico` for exact dedup, then `rapidfuzz.fuzz.WRatio` on `titulo + empresa` with a configurable threshold (default 92) for near-dups.
  - `filter_existing(offers: list[JobOffer], session) -> list[JobOffer]` — drops offers whose `hash_unico` is already in the DB for that user.
- [x] Logs how many were dropped at each stage (without dumping all titles).
- [x] Pure functions where possible; the DB-aware helper is the only one that needs a session.

## Files to create / modify
- `src/services/dedup.py`
- `tests/unit/test_dedup.py`

## Dependencies
- Phase 2 / Task 02
- Phase 1 / Task 04

## Estimated effort
**S**

## Testing notes
Hand-craft a list with: exact duplicates, near-dups (different casing / accent / wording), and unrelated. Assert correct survival counts. Test `filter_existing` against an in-memory SQLite seeded with one existing hash.
