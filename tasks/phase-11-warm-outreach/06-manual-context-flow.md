# Phase 11 · Task 06 — Manual-context flow

## Objective
When a target is `needs_manual_context`, give the user a clean way to paste 1-2 lines of context and trigger a regeneration.

## Acceptance criteria
- [ ] On `/outreach/[id]` for targets in `needs_manual_context`:
  - Prominent display of the LinkedIn URL (with disclaimer "abre y revisa manualmente").
  - Textarea labeled "Pega aquí 1-2 líneas concretas sobre esta persona o empresa" with char counter (max 500).
  - Button "Guardar y regenerar".
- [ ] Saving sends `PATCH /outreach/{id}` with `contexto_personalizacion`, then `POST /outreach/{id}/regenerate` which calls `WarmMessageWriter` with the new context.
- [ ] On successful regeneration: state moves to `draft`. On still-flagged: stays in `needs_manual_context` with an updated reason; the textarea is preserved.
- [ ] Server enforces: regeneration only allowed for `needs_manual_context` or `draft` states. Not for `sent` or `discarded`.

## Files to create / modify
- `dashboard/src/app/outreach/[id]/page.tsx` (extend)
- `dashboard/src/components/manual-context-form.tsx`
- `api/routers/outreach.py` (extend)
- `tests/integration/test_outreach_manual_context.py`

## Dependencies
- Phase 11 / Tasks 03, 05

## Estimated effort
**M**

## Testing notes
Test the state-machine: invalid state rejects regeneration; flagged → draft transition works; failing regen keeps state and updates reasons.
