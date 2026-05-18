# Phase 1 · Task 04 — DB schema + Alembic initial migration (v1 tables)

## Objective
Implement the v1 SQLAlchemy 2.x declarative models and the initial Alembic migration. Phase 11 tables are NOT included here (separate migration).

## Acceptance criteria
- [ ] `src/db/base.py` exposes `Base = DeclarativeBase` and `get_session()` (sync session factory for SQLite at `data/state.db`).
- [ ] `src/db/models.py` declares the following tables exactly as described in CLAUDE.md §6:
  - `users`
  - `companies`
  - `offers` (with `estado` enum and unique `hash_unico`)
  - `evaluations`
  - `drafts`
  - `applications`
  - `run_logs`
- [ ] All FK relationships, indexes (on `offers.user_id`, `offers.estado`, `offers.fecha_detectada`), and JSON columns set up correctly.
- [ ] Enums defined in `src/db/enums.py` (`OfferEstado`, `Recomendacion`, `MetodoEnvio`, `TipoRespuesta`).
- [ ] `alembic.ini` and `alembic/` initialized; first migration auto-generated and reviewed (no spurious diffs).
- [ ] `alembic upgrade head` creates `data/state.db` cleanly from empty.
- [ ] Smoke unit test inserts a user + offer + evaluation + draft and reads them back.

## Files to create / modify
- `src/db/__init__.py`
- `src/db/base.py`
- `src/db/models.py`
- `src/db/enums.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/<hash>_initial_v1.py`
- `tests/unit/test_db_models_smoke.py`

## Dependencies
- Phase 1 / Task 01
- Phase 1 / Task 02 (for `settings.db_url`)

## Estimated effort
**L**

## Testing notes
Smoke test uses an in-memory SQLite (`sqlite+pysqlite:///:memory:`) and applies the metadata directly (not Alembic) for speed. A separate slow test runs `alembic upgrade head` against a temp file and asserts each expected table/column exists.
