# Phase 11 · Task 05 — Dashboard outreach pages

## Objective
Three new dashboard pages for outreach: list, detail, all-targets.

## Acceptance criteria
- [ ] `/outreach` — list of outreach drafts (`OutreachTarget.estado ∈ {draft, needs_manual_context, approved}`), sortable by company priority and signal freshness, filterable by user, state, has-fresh-signal.
- [ ] `/outreach/[id]` — detail: target person info, company dossier panel, detected signals list (chronological), draft message (editable textarea, char counter), manual-context paste field (Phase 11 / Task 06), actions: `Marcar enviado`, `Regenerar con contexto nuevo`, `Descartar`.
- [ ] `/outreach/targets` — all targets across companies, including those in `needs_manual_context`. LinkedIn URL displayed prominently (target="_blank").
- [ ] Top-right counter on `/outreach`: `X/Y borradores semanales utilizados` (defaults Y=14, computed from cap × user count).
- [ ] FastAPI endpoints in `api/routers/outreach.py`: `GET /users/{username}/outreach`, `GET /outreach/{id}`, `PATCH /outreach/{id}`, `POST /outreach/{id}/mark-sent`, `POST /outreach/{id}/regenerate`, `POST /outreach/{id}/discard`, `GET /users/{username}/outreach/targets`.
- [ ] Sidebar nav gets an `Outreach` group with the three pages.
- [ ] All UI strings in Spanish.

## Files to create / modify
- `dashboard/src/app/outreach/page.tsx`
- `dashboard/src/app/outreach/[id]/page.tsx`
- `dashboard/src/app/outreach/targets/page.tsx`
- `dashboard/src/components/outreach-*.tsx`
- `api/routers/outreach.py`
- `api/main.py` (register router)

## Dependencies
- Phase 11 / Tasks 01-04
- Phase 8 (dashboard scaffolding)

## Estimated effort
**L**

## Testing notes
Integration test for the API endpoints. Manual smoke for the UI.
