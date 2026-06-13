# Phase 10.6 · Task 02 — Offers list API (read-only, per-user, all states)

## Objective
Expose every scraped offer **for a given user** through the FastAPI backend,
regardless of analysis state, so the dashboard can show offers that never reached
a draft (`nueva`, `filtrada`, `descartada`, `investigada`, `evaluada`, …). Today
only draft-backed offers are reachable (`api/routers/drafts.py`).

## Acceptance criteria
- [x] New router `api/routers/offers.py` with `GET /users/{username}/offers`.
      Scoped to that user via `Offer.user_id` (join offers→user), newest
      `fecha_detectada` first, paginated (`page`, `page_size`, default 50, max 200).
      _Implemented; pagination param is `per_page` (default 50, `ge=1, le=200`) to
      match the existing drafts/history responses, not `page_size`. Order
      `fecha_detectada.desc(), id.desc()`._
- [x] Query params: `estado` (optional, one of `OfferEstado`; omitted = all),
      `plataforma` (optional: `adzuna`/`jooble`), free-text `q` over
      `titulo`/`empresa` (optional). Invalid `estado` ⇒ 422.
      _`estado` validated against `frozenset(OfferEstado)` → 422;
      `plataforma`→`Offer.fuente`; `q`→`ilike` over titulo/empresa._
- [x] Response per-row: `id`, `titulo`, `empresa`, `ubicacion`,
      `fuente`/`plataforma`, `url`, `fecha_publicacion`, `fecha_detectada`,
      `estado`, `razon_descarte` (when present), and `has_draft` /
      `has_evaluation` booleans so the UI can deep-link analyzed ones.
      _`OfferListItem`; `has_draft`/`has_evaluation` computed via correlated
      `EXISTS` subqueries (no N+1)._
- [x] Companion `GET /users/{username}/offers/counts` returning a per-user
      `{estado: count}` map (drives the filter chips + "X sin analizar" badge).
      One grouped query, not N.
      _`offer_counts`: single `group_by(Offer.estado)` query → `OfferCountsResponse`
      (`counts` map + `total`)._
- [x] Reuses the existing `OfferOut` schema where possible; new list-item +
      counts schemas added to `api/schemas.py` only for the extra fields. Router
      registered in `api/main.py`.
      _Added `OfferListItem`/`OfferListResponse`/`OfferCountsResponse`; router
      registered after `history.router`._
- [x] `mypy --strict` passes on touched `api/` code; router test (mocked DB)
      covering: per-user scoping (user A does not see user B's offers), `estado`
      filter, bad `estado` 422, and the counts endpoint.
      _mypy --strict green on offers/schemas/main; `tests/integration/test_api_offers.py`
      (7 tests, TestClient + in-memory SQLite) covers all-states list, per-user
      scoping with a shared hash, estado filter, plataforma/flags, 422, 404, counts._

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
