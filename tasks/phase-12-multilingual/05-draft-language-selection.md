# Phase 12 · Task 05 — Draft language selection

> **v2 scope.** Requires explicit user approval after v1 + v1.1.

## Objective
Decide, per offer, which language the application draft is written in, and surface that choice in the dashboard.

## Acceptance criteria
- [ ] Draft language is chosen by a clear rule: posting language (detected) → fall back to the offer's country default language → fall back to the user's primary `search_languages` entry.
- [ ] `Draft` / `drafts` table records the `idioma` of each draft.
- [ ] `ApplicationWriter` selects the matching prompt locale (Task 04) for that language.
- [ ] Dashboard draft detail shows the draft language; history/list can filter by language.
- [ ] Telegram daily summary notes per-language counts.

## Files to create / modify
- `src/models/draft.py`, `src/db/models.py` (+ Alembic migration for `idioma`)
- `src/agents/application_writer.py`
- `dashboard/...`, `api/...`
- `src/services/telegram.py`
- `tests/...`

## Dependencies
- Phase 12 / Task 01, 04

## Estimated effort
**M**
