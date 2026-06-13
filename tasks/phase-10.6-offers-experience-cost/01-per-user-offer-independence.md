# Phase 10.6 · Task 01 — Per-user offer independence (composite unique + migration)

## Objective
Make scraped offers truly independent per user, so the same public job can exist
once **per user** (Jorge's queue ≠ Madalina's). Today `offers.user_id` exists and
`filter_existing` is user-scoped, but a **global** `UniqueConstraint("hash_unico")`
means once user A stores offer X, user B's insert of the same X raises
`IntegrityError` — silently dropping real offers for the second user.

## Acceptance criteria
- [x] `Offer.__table_args__` unique constraint changes from global
      `UniqueConstraint("hash_unico", name="uq_offers_hash_unico")` to composite
      `UniqueConstraint("user_id", "hash_unico", name="uq_offers_user_hash")`.
      _Done in `src/db/models.py`; `test_offers_composite_unique_exists` asserts the
      reflected constraint name + `["user_id", "hash_unico"]` columns._
- [x] Alembic migration created (`alembic/versions/`) that drops the old unique
      constraint/index and adds the composite one. SQLite-safe (batch alter if
      needed — SQLite cannot drop a named constraint in place). Upgrade **and**
      downgrade implemented.
      _`e3f4a5b6c7d8_offer_composite_unique.py`, down_revision `d1e2f3a4b5c6`;
      `op.batch_alter_table` drop_constraint + create_unique_constraint both ways
      (env.py already sets `render_as_batch=True`)._
- [x] Existing per-user query paths unchanged in behavior: `filter_existing`
      already scopes by `user_id`; confirm dedup-within-run still keys on
      `hash_unico` (per run, pre-user-scoping) — that is correct and stays.
      _No change to `src/services/dedup.py` or `scrape_runner.py`; their existing
      tests (`test_dedup`, `test_scrape_runner`, `test_scrape_pipeline`) stay green._
- [x] No cross-user data leak: `scrape_runner.run_scrape` for two different users
      can persist the same offer hash as two distinct rows (one per `user_id`).
      _`test_same_hash_allowed_across_users` (ORM) +
      `test_upgrade_allows_same_hash_across_users` (post-migration) prove two users
      hold the same hash as distinct rows._
- [x] `mypy --strict` passes; migration runs clean on a fresh DB and on a DB seeded
      with pre-migration data (no duplicate `(user_id, hash_unico)` rows exist, so
      the composite constraint applies without conflict).
      _mypy --strict green on models + migration + migration test; the integration
      test upgrades over seeded pre-migration data and round-trips up/down._
- [x] Test: seed offer X for user A, scrape same X for user B → two rows, no error;
      scrape X again for user A → still deduped to one row for A.
      _Covered: cross-user allowed (above) + `test_same_user_same_hash_rejected`
      shows same-user duplicate hash raises IntegrityError._

## Implementation notes
- `src/db/models.py` lines ~85–90 hold the `Offer.__table_args__`. The
  `ix_offers_user_id` and `ix_offers_estado` indexes stay.
- SQLite limitation: dropping a unique constraint requires `op.batch_alter_table`
  in the migration (recreate-table strategy). Use Alembic's batch context.
- This is a **data-correctness prerequisite** for the per-user offers view
  (Task 02/03) — do it first.

## Files to create / modify
- `src/db/models.py`
- `alembic/versions/<new>_offer_composite_unique.py` (new)
- `tests/unit/test_dedup.py` or `tests/integration/test_scrape_runner.py` (extend)

## Dependencies
- None. First task of the phase.

## Estimated effort
**S–M**

## Testing notes
Integration test against a temp SQLite DB: run the migration, then assert two users
can hold the same `hash_unico` while a single user still dedups. Verify `downgrade`
restores the prior schema without error.
