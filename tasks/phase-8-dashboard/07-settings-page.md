# Phase 8 · Task 07 — `/settings` page (read-only profile)

## Objective
Display the user's YAML profile as a read-only summary, so the user can verify what the agents are seeing.

## Acceptance criteria
- [x] `app/settings/page.tsx` fetches `GET /users/{username}/profile` and renders sections: Datos personales, Objetivos (roles + sectores + stack), Idiomas, Preferencias (modalidad, ubicación, salario mínimo), Red flags, Resumen CV, Experiencias, Educación, Certificaciones.
- [x] Note at the top: "Para editar, modifica `config/users/<username>.yaml` y vuelve a ejecutar `profile load`."
- [x] No edit affordances. Read-only by design for v1.

## Files to create / modify
- `dashboard/src/app/settings/page.tsx`

## Dependencies
- Phase 8 / Tasks 01, 02

## Estimated effort
**S**

## Testing notes
Manual smoke. Verify long fields wrap nicely on mobile.
