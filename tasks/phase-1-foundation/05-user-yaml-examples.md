# Phase 1 · Task 05 — User YAML schema, examples, loader

## Objective
Provide concrete `*.yaml.example` profiles for both users and a CLI command that loads + validates a YAML profile and inserts/updates the corresponding `users` row.

## Acceptance criteria
- [ ] `config/users/jorge.yaml.example` and `config/users/madalina.yaml.example` are realistic skeletons covering every `UserProfile` field. CV summary is in Spanish.
- [ ] Real YAMLs (`jorge.yaml`, `madalina.yaml`) are gitignored; the loader expects them at the same path.
- [ ] `src/services/profiles.py` exposes `load_profile(username: str) -> UserProfile` and `upsert_user_row(profile: UserProfile) -> None`.
- [ ] CLI command `python -m src.cli profile load --user <username>` validates the YAML, prints a one-line summary, and upserts into the `users` table.
- [ ] Invalid YAML produces a clear error pointing to the offending field, not a stack dump.

## Files to create / modify
- `config/users/jorge.yaml.example`
- `config/users/madalina.yaml.example`
- `src/services/profiles.py`
- `src/cli.py` (add `profile load` subcommand — full CLI structure comes in Task 06; this task may temporarily stub it)
- `tests/unit/test_profile_loader.py`

## Dependencies
- Phase 1 / Task 03
- Phase 1 / Task 04

## Estimated effort
**M**

## Testing notes
Test loads the example YAMLs (rename for the test) and asserts a valid `UserProfile`. Test a deliberately broken YAML and assert the error message references the failing field.
