# Phase 8 · Task 06 — `/history` page

## Objective
Applied offers with response status and simple stats.

## Acceptance criteria
- [x] `app/history/page.tsx` fetches `GET /users/{username}/history`.
- [x] Tabs: Aplicadas / Entrevistas / Rechazos / Otros.
- [x] Each row: empresa, título, fecha envío, plataforma, respuesta recibida (yes/no), tipo respuesta, fecha respuesta, notas (read-only).
- [x] Top stats strip: total enviadas (últimos 30/90 días), tasa de respuesta, tasa de entrevista.
- [x] Sort by `fecha_envio` desc by default.

## Implementation notes
- Route is `/[username]/history`. Tabs are URL-driven (`?state=`); they map to the API's existing filter values: Aplicadas→`applied` (sin respuesta), Entrevistas→`interview` (en_proceso), Rechazos→`rejected` (negativa), Otros→`hired` (positiva).
- "Plataforma" column = `offer_fuente`. Sort desc is done server-side by the API.
- Stats are computed from a second unfiltered fetch so they stay constant across tabs; time logic lives in `lib/stats.ts` (kept out of the component to satisfy the `react-hooks/purity` lint rule).

## Files to create / modify
- `dashboard/src/app/history/page.tsx`
- `dashboard/src/components/history-stats.tsx`

## Dependencies
- Phase 8 / Tasks 01, 02

## Estimated effort
**M**

## Testing notes
Manual smoke against seeded data.
