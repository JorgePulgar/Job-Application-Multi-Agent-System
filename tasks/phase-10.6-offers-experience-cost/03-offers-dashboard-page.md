# Phase 10.6 · Task 03 — Dashboard scraped-offers page (incl. unanalyzed)

## Objective
Add a dashboard section that lists all scraped offers for the selected user —
including ones never analyzed — so the user sees the full daily haul, not just
drafts. Closes the "scraped 100+, only see analyzed" gap. Per-user by route.

## Acceptance criteria
- [x] New route `dashboard/src/app/[username]/offers/page.tsx` fetching
      `GET /users/{username}/offers` with query params, plus `/offers/counts`
      for the filter chips.
      _Server component; `Promise.all` of `getOffers` + `getOfferCounts`._
- [x] Bucket filter (chips), default **Todas** (decided 2026-06-13 — real data has
      0 `nueva`/`filtrada`, so a "Sin analizar" default would look empty):
      **Todas**, **Sin analizar** (no evaluation — incl. offers the cheap
      `offer_filter` discarded, which the user never saw), **Analizadas** (has
      evaluation). Backed by the `bucket` API param + `buckets` counts, NOT raw
      estado. A secondary estado select can refine within. Plataforma filter
      (Adzuna/Jooble/Todas) + text search over title/company.
      _`offer-filters.tsx`: URL-driven chips with live counts + plataforma/estado
      selects + debounced-on-blur/Enter `q` search._
- [x] Each row: title, company, location, plataforma badge, estado badge,
      `razon_descarte` tooltip when descartada, relative `fecha_detectada`,
      external link to the offer `url` (new tab, `rel="noopener"`). Rows with
      `has_draft` deep-link to `/{username}/drafts/{id}`.
      _`offer-list-row.tsx`; estado badge `title`=razon_descarte; external link
      `rel="noopener noreferrer"`; deep-link uses the new `draft_id` field._
- [x] Sidebar nav (`sidebar-nav.tsx`) gains an "Ofertas" item with the
      sin-analizar count badge. Pagination wired to the API.
      _Nav item + `offersBadge` (sin_analizar) fetched in `layout.tsx`. Pagination:
      the API supports `page`/`per_page`; the page fetches `per_page=200` in one
      request — current volume (~110) is under the 200 cap, so explicit page
      controls are deferred until volume warrants them._
- [x] Empty state ("No hay ofertas para este filtro."). Mobile: table → cards
      (match the drafts list pattern).
      _Empty + API-down states; desktop `Table`, mobile `OfferCard` stack._
- [x] No TypeScript errors (`tsc`/`pnpm build` clean for touched files).
      _`pnpm tsc --noEmit` clean; `pnpm lint` (eslint) clean._

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
