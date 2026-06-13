# Phase 10.6 · Task 03 — Dashboard scraped-offers page (incl. unanalyzed)

## Objective
Add a dashboard section that lists all scraped offers for the selected user —
including ones never analyzed — so the user sees the full daily haul, not just
drafts. Closes the "scraped 100+, only see analyzed" gap. Per-user by route.

## Acceptance criteria
- [ ] New route `dashboard/src/app/[username]/offers/page.tsx` fetching
      `GET /users/{username}/offers` with query params, plus `/offers/counts`
      for the filter chips.
- [ ] Estado filter (chips or select): **Sin analizar** (`nueva`+`filtrada`),
      **Descartadas** (`descartada`), **Analizadas** (`evaluada`+
      `borrador_generado`+`enviada`), **Todas**. Default **Sin analizar**.
      Plataforma filter (Adzuna/Jooble/Todas) + text search over title/company.
- [ ] Each row: title, company, location, plataforma badge, estado badge,
      `razon_descarte` tooltip when descartada, relative `fecha_detectada`,
      external link to the offer `url` (new tab, `rel="noopener"`). Rows with
      `has_draft` deep-link to `/{username}/drafts/{id}`.
- [ ] Sidebar nav (`sidebar-nav.tsx`) gains an "Ofertas" item with the
      sin-analizar count badge. Pagination wired to the API.
- [ ] Empty state ("No hay ofertas para este filtro."). Mobile: table → cards
      (match the drafts list pattern).
- [ ] No TypeScript errors (`tsc`/`pnpm build` clean for touched files).

## Implementation notes
- Mirror existing drafts list patterns: `draft-list-row.tsx`, `draft-filters.tsx`,
  `ui/table.tsx`, `ui/badge.tsx`, `ui/tabs.tsx`.
- API client lives alongside the existing dashboard fetch helpers.
- Read-only view — no "analyze this offer" action yet (later ask). Keep it a list.

## Files to create / modify
- `dashboard/src/app/[username]/offers/page.tsx` (new)
- `dashboard/src/components/offer-list-row.tsx` (new) + `offer-filters.tsx` (new)
- `dashboard/src/components/sidebar-nav.tsx` (nav item + badge)
- dashboard API client helper (extend existing)

## Dependencies
- Task 02 (offers API).

## Estimated effort
**M**

## Testing notes
Manual smoke test against the seeded API. Default filter shows unanalyzed offers;
plataforma/text filters work; external links open source URL; analyzed rows
deep-link to their draft. Optional Playwright on filter switching.
