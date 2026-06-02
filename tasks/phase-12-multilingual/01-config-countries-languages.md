# Phase 12 · Task 01 — Per-user target countries + search languages

> **v2 scope.** Requires explicit user approval, only after v1 (Phase 10) and v1.1 (Phase 11) are done. Do not start without it.

## Objective
Make country and language first-class, user-configurable inputs. Today the system is hardcoded to Spain + Spanish. v2 lets each user request one or more **target countries** and the system searches in both **Spanish and English** (configurable per user).

## Acceptance criteria
- [ ] `UserProfile` gains `target_countries: list[str]` (ISO 3166-1 alpha-2, e.g. `["es", "gb", "de"]`, default `["es"]`) and `search_languages: list[str]` (ISO 639-1, e.g. `["es", "en"]`, default `["es"]`), validated.
- [ ] `config/sources.yaml` defines, per platform, which countries/locales it supports and how the country maps to the platform's API (e.g. Adzuna country path segment, Jooble country, WTTJ locale).
- [ ] Validation rejects a `target_country` a chosen platform cannot serve, with a clear error listing supported countries.
- [ ] Backward compatible: an existing profile with no new fields behaves exactly as v1 (Spain + Spanish).
- [ ] `*.yaml.example` profiles updated to show the new fields commented/with defaults.

## Files to create / modify
- `src/models/user_profile.py`
- `config/sources.yaml`
- `config/users/*.yaml.example`
- `tests/unit/test_user_profile_models.py`

## Dependencies
- v1 + v1.1 complete

## Estimated effort
**M**
