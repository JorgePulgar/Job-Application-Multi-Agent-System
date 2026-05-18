# Phase 8 · Task 05 — `/drafts/[id]` detail + P.S. toggle

## Objective
The main user-facing screen: review a draft, edit it, decide what to do.

## Acceptance criteria
- [ ] `app/drafts/[id]/page.tsx` fetches `GET /drafts/{id}` and renders:
  - Original offer panel (title, company, location, modality, salary, link to source, full description in a collapsible block).
  - Company dossier panel (markdown rendered, fuentes as outbound links).
  - Evaluation panel (score, ventajas, desventajas, red flags, reasoning).
  - Draft panel: editable Subject, editable Email body (textarea, monospace), editable Cover letter (textarea).
  - "Experiencias destacadas" list (read-only).
- [ ] Action buttons: `Marcar como enviado` (opens a small dialog: method `email|formulario|easy_apply|manual` + optional notes), `Regenerar`, `Descartar`.
- [ ] Optional **P.S. toggle**: switch labeled "Añadir P.D. sobre asistencia IA". When on, a default P.S. text (configurable in user profile) is appended to the email body on send. The toggle and text are user-facing only — agent never sets them.
- [ ] All edits send `PATCH /drafts/{id}` (add to API in Task 01 if missing — small inline addition) before marking as sent.
- [ ] Mobile: stacked panels, sticky action bar at bottom.

## Files to create / modify
- `dashboard/src/app/drafts/[id]/page.tsx`
- `dashboard/src/components/draft-editor.tsx`
- `dashboard/src/components/offer-panel.tsx`
- `dashboard/src/components/company-dossier-panel.tsx`
- `dashboard/src/components/evaluation-panel.tsx`
- `dashboard/src/components/draft-actions.tsx`
- `api/routers/drafts.py` (add `PATCH /drafts/{id}` if not present)

## Dependencies
- Phase 8 / Tasks 01, 02, 04

## Estimated effort
**L**

## Testing notes
Manual smoke test for each action. Verify the P.S. text is added only when the toggle is on and is excluded from regeneration prompts (the agent must never see it).
