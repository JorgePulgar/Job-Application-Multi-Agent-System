# Phase 6 · Task 05 — Persist drafts (DB + markdown files)

## Objective
Each draft goes into the `drafts` table AND is written as a markdown file to `data/drafts/{user}/{YYYY-MM-DD}_{slug}.md` for easy offline review.

## Acceptance criteria
- [ ] `src/services/draft_persistence.py` exposes `save_draft(draft, offer, user, db_session) -> Path`.
- [ ] DB insert: idempotent on `offer_id` (one draft per offer; rewriting updates `email_subject`, `email_body`, `carta_presentacion`, `fecha_generacion`).
- [ ] Filename slug = `slugify(empresa + "_" + titulo)[:80]`.
- [ ] Markdown file structure: frontmatter (`offer_url`, `empresa`, `score`, `recomendacion`, `needs_manual_context`) + body sections (Subject, Email body, Cover letter, Highlighted experiences).
- [ ] On `needs_manual_context=True`, file still written with `flagged_reasons` clearly noted at top.
- [ ] Offer `estado` set to `draft_ready` (or stays in `evaluated` if `needs_manual_context`).

## Files to create / modify
- `src/services/draft_persistence.py`
- `tests/unit/test_draft_persistence.py`

## Dependencies
- Phase 6 / Tasks 01-04

## Estimated effort
**M**

## Testing notes
Test idempotency (calling save twice updates rather than duplicates). Verify file content structure. Verify path safe-handles weird characters in company/title.
