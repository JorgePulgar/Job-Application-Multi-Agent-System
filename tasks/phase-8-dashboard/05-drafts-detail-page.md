# Phase 8 · Task 05 — `/drafts/[id]` detail + P.S. toggle

## Objective
The main user-facing screen: review a draft, edit it, decide what to do.

## Acceptance criteria
- [x] `app/drafts/[id]/page.tsx` fetches `GET /drafts/{id}` and renders:
  - Original offer panel (title, company, location, modality, salary, link to source, full description in a collapsible block).
  - Company dossier panel (markdown rendered, fuentes as outbound links).
  - Evaluation panel (score, ventajas, desventajas, red flags, reasoning).
  - Draft panel: editable Subject, editable Email body (textarea, monospace), editable Cover letter (textarea).
  - "Experiencias destacadas" list (read-only).
- [x] Action buttons: `Marcar como enviado` (opens a small dialog: method `email|formulario|easy_apply|manual` + optional notes), `Regenerar`, `Descartar`.
- [x] Optional **P.S. toggle**: switch labeled "Añadir P.D. sobre asistencia IA". When on, a default P.S. text (configurable in user profile) is appended to the email body on send. The toggle and text are user-facing only — agent never sets them.
- [x] All edits send `PATCH /drafts/{id}` (add to API in Task 01 if missing — small inline addition) before marking as sent.
- [x] Mobile: stacked panels, sticky action bar at bottom.

## Implementation notes
- Route is `/[username]/drafts/[id]`; PATCH `/drafts/{id}` added to `api/routers/drafts.py` (+ `DraftPatchRequest` schema, 3 API tests).
- **Salary** has no DB column → shown as "—". **Modality** inferred from offer text (`inferModality`).
- `dossier_json` is the structured `CompanyDossier` (not markdown) → rendered as fields + `fuentes` links.
- **P.S.** is client-side only: appended in the copy/preview and recorded via `mark-sent`'s `ps_text`; never PATCHed into the body, so `regenerate` never sees it. Default text read from optional profile key `ps_asistencia_ia`, else a built-in constant.
- **Experiencias destacadas** uses the profile's full `experiences` list (no per-offer highlight data exists).
- mark-sent method values are the task's `email|formulario|easy_apply|manual` (stored in the free-form `metodo_envio` column).
- Built lightweight `Switch` + mark-sent dialog inline (no shadcn switch/dialog primitive present).

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
