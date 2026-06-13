# Phase 10.6 · Task 01 — Per-user offer independence (composite unique + migration)

## Objective
Make scraped offers truly independent per user, so the same public job can exist
once **per user** (Jorge's queue ≠ Madalina's). Today `offers.user_id` exists and
`filter_existing` is user-scoped, but a **global** `UniqueConstraint("hash_unico")`
means once user A stores offer X, user B's insert of the same X raises
`IntegrityError` — silently dropping real offers for the second user.

## Acceptance criteria
- [ ] `Offer.__table_args__` unique constraint changes from global
      `UniqueConstraint("hash_unico", name="uq_offers_hash_unico")` to composite
      `UniqueConstraint("user_id", "hash_unico", name="uq_offers_user_hash")`.
- [ ] Alembic migration created (`alembic/versions/`) that drops the old unique
      constraint/index and adds the composite one. SQLite-safe (batch alter if
      needed — SQLite cannot drop a named constraint in place). Upgrade **and**
      downgrade implemented.
- [ ] Existing per-user query paths unchanged in behavior: `filter_existing`
      already scopes by `user_id`; confirm dedup-within-run still keys on
      `hash_unico` (per run, pre-user-scoping) — that is correct and stays.
- [ ] No cross-user data leak: `scrape_runner.run_scrape` for two different users
      can persist the same offer hash as two distinct rows (one per `user_id`).
- [ ] `mypy --strict` passes; migration runs clean on a fresh DB and on a DB seeded
      with pre-migration data (no duplicate `(user_id, hash_unico)` rows exist, so
      the composite constraint applies without conflict).
- [ ] Test: seed offer X for user A, scrape same X for user B → two rows, no error;
      scrape X again for user A → still deduped to one row for A.

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
