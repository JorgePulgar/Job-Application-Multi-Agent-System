# Phase 8 · Task 04 — `/drafts` list page

## Objective
List of `draft_ready` offers for the selected user, sortable and filterable.

## Acceptance criteria
- [ ] `app/drafts/page.tsx` fetches `GET /users/{username}/drafts` with query params.
- [ ] Sort by: score (default desc), date generated, company name.
- [ ] Filter by: platform (Adzuna/Jooble/WTTJ), sector, recomendacion (aplicar/dudar), needs_manual_context.
- [ ] Each row: company logo placeholder, title, location, modality, score badge, recomendacion badge, "needs manual context" badge if applicable, link to `/drafts/{id}`.
- [ ] Empty state ("No hay borradores. Ejecuta una pasada del orquestador.").
- [ ] Mobile: table → cards.

## Files to create / modify
- `dashboard/src/app/drafts/page.tsx`
- `dashboard/src/components/draft-list-row.tsx`
- `dashboard/src/components/draft-filters.tsx`

## Dependencies
- Phase 8 / Tasks 01, 02, 03

## Estimated effort
**M**

## Testing notes
Manual smoke test against seeded API. Optional Playwright test verifying filter+sort interactions.
