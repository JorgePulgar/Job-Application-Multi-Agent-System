# Phase 12 · Task 03 — Bilingual search keyword expansion

> **v2 scope.** Requires explicit user approval after v1 + v1.1.

## Objective
When `search_languages` includes English, search queries and keyword matching must work in English as well as Spanish, so a Spanish-speaking candidate also catches English-language postings (common in EU tech roles).

## Acceptance criteria
- [ ] Search query terms derived from `target_roles` are expanded per `search_languages` (e.g. "Ingeniero de datos" + "Data Engineer").
- [ ] Role/keyword synonym mapping lives in config, not hardcoded in agents.
- [ ] Offer filter's relevance keyword matching is accent- and language-insensitive for the configured languages.
- [ ] No duplicate offers when the same posting is found via both the ES and EN query (dedup covers it).

## Files to create / modify
- `config/sources.yaml` or a new `config/keywords.yaml`
- `src/agents/job_scraper/*` (query building)
- `src/agents/offer_filter.py` (if matching logic is here)
- `tests/unit/...`

## Dependencies
- Phase 12 / Task 01, 02

## Estimated effort
**M**
