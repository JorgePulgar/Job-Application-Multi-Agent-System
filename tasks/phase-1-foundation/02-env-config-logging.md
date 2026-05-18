# Phase 1 · Task 02 — Env / config / logging

## Objective
Centralize environment variable loading, app config, and structured logging so every subsequent module reads them from one place. Mask PII in log output.

## Acceptance criteria
- [ ] `.env.example` committed with every variable listed in CLAUDE.md §5, including comments and defaults.
- [ ] `src/config.py` exposes a Pydantic `Settings` model loaded from env (`pydantic-settings` or manual `model_validate` from `os.environ`). All fields typed. Missing required vars raise on startup with a clear message.
- [ ] `src/logging_setup.py` configures `structlog` with JSON output in CI and pretty console output locally (toggle via env). Includes a processor that masks emails and phone numbers in any logged value.
- [ ] PII masking covered by a unit test (regex coverage for typical emails and Spanish phone formats).
- [ ] `src/__init__.py` exposes `get_settings()` and `configure_logging()` for use from other modules.
- [ ] No secret values ever appear in repo or example file — only placeholders.

## Files to create / modify
- `.env.example`
- `src/config.py`
- `src/logging_setup.py`
- `tests/unit/test_logging_pii_mask.py`

## Dependencies
- Phase 1 / Task 01

## Estimated effort
**S**

## Testing notes
Unit test: feed strings containing fake emails/phones through the masking processor and assert output is redacted. Verify that a missing required env var raises a clear error message (not a cryptic `ValidationError` dump).
