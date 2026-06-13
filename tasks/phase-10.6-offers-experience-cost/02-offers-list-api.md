# Phase 10.6 · Task 02 — Offers list API (read-only, per-user, all states)

## Objective
Expose every scraped offer **for a given user** through the FastAPI backend,
regardless of analysis state, so the dashboard can show offers that never reached
a draft (`nueva`, `filtrada`, `descartada`, `investigada`, `evaluada`, …). Today
only draft-backed offers are reachable (`api/routers/drafts.py`).

## Acceptance criteria
- [ ] New router `api/routers/offers.py` with `GET /users/{username}/offers`.
      Scoped to that user via `Offer.user_id` (join offers→user), newest
      `fecha_detectada` first, paginated (`page`, `page_size`, default 50, max 200).
- [ ] Query params: `estado` (optional, one of `OfferEstado`; omitted = all),
      `plataforma` (optional: `adzuna`/`jooble`), free-text `q` over
      `titulo`/`empresa` (optional). Invalid `estado` ⇒ 422.
- [ ] Response per-row: `id`, `titulo`, `empresa`, `ubicacion`,
      `fuente`/`plataforma`, `url`, `fecha_publicacion`, `fecha_detectada`,
      `estado`, `razon_descarte` (when present), and `has_draft` /
      `has_evaluation` booleans so the UI can deep-link analyzed ones.
- [ ] Companion `GET /users/{username}/offers/counts` returning a per-user
      `{estado: count}` map (drives the filter chips + "X sin analizar" badge).
      One grouped query, not N.
- [ ] Reuses the existing `OfferOut` schema where possible; new list-item +
      counts schemas added to `api/schemas.py` only for the extra fields. Router
      registered in `api/main.py`.
- [ ] `mypy --strict` passes on touched `api/` code; router test (mocked DB)
      covering: per-user scoping (user A does not see user B's offers), `estado`
      filter, bad `estado` 422, and the counts endpoint.

## Implementation notes
- `Offer.user_id` (FK) + `ix_offers_user_id` + `ix_offers_estado` exist — scoping
  and filtering are cheap.
- "Unanalyzed" = `estado in {nueva, filtrada}`. `descartada` = analyzed-and-rejected,
  keep separate in the UI. Final grouping decided with Task 03.
- Read-only router. No state transitions here.
- Depends on Task 01 so per-user rows actually exist independently.

## Files to create / modify
- `api/routers/offers.py` (new)
- `api/schemas.py` (list-item + counts schemas)
- `api/main.py` (register router)
- `tests/unit/test_api_offers.py` (new)

## Dependencies
- Task 01 (per-user offer independence).

## Estimated effort
**M**

## Testing notes
Unit test against a seeded SQLite session: seed offers for two users across several
`estado` values + both platforms; assert per-user scoping, filtering, pagination,
counts, and the `has_draft`/`has_evaluation` flags.
