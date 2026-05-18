# Phase 8 · Task 06 — `/history` page

## Objective
Applied offers with response status and simple stats.

## Acceptance criteria
- [ ] `app/history/page.tsx` fetches `GET /users/{username}/history`.
- [ ] Tabs: Aplicadas / Entrevistas / Rechazos / Otros.
- [ ] Each row: empresa, título, fecha envío, plataforma, respuesta recibida (yes/no), tipo respuesta, fecha respuesta, notas (read-only).
- [ ] Top stats strip: total enviadas (últimos 30/90 días), tasa de respuesta, tasa de entrevista.
- [ ] Sort by `fecha_envio` desc by default.

## Files to create / modify
- `dashboard/src/app/history/page.tsx`
- `dashboard/src/components/history-stats.tsx`

## Dependencies
- Phase 8 / Tasks 01, 02

## Estimated effort
**M**

## Testing notes
Manual smoke against seeded data.
