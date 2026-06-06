# Phase 8 · Task 04 — `/drafts` list page

## Objective
List of `draft_ready` offers for the selected user, sortable and filterable.

## Acceptance criteria
- [x] `app/drafts/page.tsx` fetches `GET /users/{username}/drafts` with query params.
- [x] Sort by: score (default desc), date generated, company name.
- [x] Filter by: platform (Adzuna/Jooble/WTTJ), sector, recomendacion (aplicar/dudar), needs_manual_context.
- [x] Each row: company logo placeholder, title, location, modality, score badge, recomendacion badge, "needs manual context" badge if applicable, link to `/drafts/{id}`.
- [x] Empty state ("No hay borradores. Ejecuta una pasada del orquestador.").
- [x] Mobile: table → cards.

## Implementation notes
- Route is `/[username]/drafts` (committed in task 02), so the row link is `/{username}/drafts/{id}`.
- `recomendacion` values are the real enum `solicitar`/`considerar`/`descartar` (labelled in Spanish), not `aplicar`/`dudar` from the brief.
- `needs_manual_context` filter is exposed via the Estado select (Listos / Contexto manual / Todos), since it is a `Draft.estado` value.
- **Modality** has no DB column; inferred best-effort from offer title/location text (`inferModality`). May be blank.
- API extended (task-01 code) to support this view: added `company_sector` to the drafts response, a `sector` filter, and `sort=company`.

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
