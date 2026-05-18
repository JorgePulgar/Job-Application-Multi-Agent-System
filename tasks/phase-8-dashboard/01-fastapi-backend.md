# Phase 8 · Task 01 — FastAPI backend

## Objective
Read/write API exposing the SQLite DB to the Next.js dashboard.

## Acceptance criteria
- [ ] `api/main.py` (FastAPI app) with routers:
  - `GET /users` — list usernames
  - `GET /users/{username}/drafts?state=draft_ready&sort=score&platform=&recomendacion=` — paginated draft listings (joined with offer + company + evaluation)
  - `GET /drafts/{draft_id}` — full detail (offer + company dossier + evaluation + draft body)
  - `POST /drafts/{draft_id}/mark-sent` — body: `{method, notes?, ps_text?}`. Creates `applications` row, sets offer `estado='applied'`.
  - `POST /drafts/{draft_id}/discard` — sets offer `estado='discarded'` with `razon_descarte='manual_review'`.
  - `POST /drafts/{draft_id}/regenerate` — enqueues a regeneration (sync for v1: calls `ApplicationWriter` inline).
  - `GET /users/{username}/history?state=applied|rejected|interview|hired&from=&to=` — application history.
  - `GET /users/{username}/profile` — read-only YAML contents as JSON.
- [ ] All endpoints typed with Pydantic response models.
- [ ] CORS configured to allow the Vercel dashboard origin (env-driven).
- [ ] Single SQLAlchemy session per request (FastAPI dependency).

## Files to create / modify
- `api/main.py`
- `api/routers/{drafts,users,history,profile}.py`
- `api/schemas.py`
- `api/deps.py`
- `tests/integration/test_api.py`

## Dependencies
- Phase 6 / Task 05
- Phase 7 (regeneration endpoint reuses orchestrator pieces)

## Estimated effort
**L**

## Testing notes
FastAPI `TestClient` against in-memory SQLite, seeded with fixtures. Verify each endpoint shape and state transitions.
