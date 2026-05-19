# Phase 1 · Task 01 — Project scaffolding

## Objective
Set up the Python project with `uv` and configure the baseline quality tooling (`ruff`, `mypy --strict`, `pytest`, pre-commit). Lay down the directory tree from CLAUDE.md so subsequent tasks have a place to put code.

## Acceptance criteria
- [x] `pyproject.toml` declares Python `>=3.11`, project metadata, and runtime/dev dependency groups via `uv`.
- [x] Runtime deps installed: `openai`, `httpx`, `beautifulsoup4`, `playwright`, `sqlalchemy`, `alembic`, `pydantic`, `structlog`, `click`, `pyyaml`, `python-dotenv`, `rapidfuzz`.
- [x] Dev deps: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `respx`, `pre-commit`, `types-PyYAML`.
- [x] `ruff` configured (line length 100, target py311, sensible rule set).
- [x] `mypy` configured with `strict = true` for `src/` and `api/`.
- [x] `pytest` configured with `tests/` as test root and `pytest-asyncio` mode `auto`.
- [x] `.pre-commit-config.yaml` runs `ruff`, `ruff format`, `mypy`, `pytest -q`.
- [x] `.gitignore` covers `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `data/state.db`, `data/drafts/`, `config/users/*.yaml` (allow `*.example`), `.env`, `node_modules`, `.next`.
- [x] Empty package skeleton present: `src/__init__.py`, `src/models/`, `src/db/`, `src/agents/{job_scraper}/`, `src/services/`, `src/prompts/`, `api/`, `tests/{unit,integration}/`, `data/.gitkeep`.
- [x] `uv sync` succeeds from a clean state.
- [x] `ruff check`, `ruff format --check`, `mypy --strict src/`, `pytest -q` all run green (even if no tests yet).

## Files to create / modify
- `pyproject.toml`
- `.gitignore`
- `.pre-commit-config.yaml`
- Empty `__init__.py` files under each `src/` subpackage
- `data/.gitkeep`

## Dependencies
None (this is the first task).

## Estimated effort
**M** — fiddly tooling, no real logic.

## Testing notes
No application tests yet. Verify by running `uv sync && ruff check && ruff format --check && mypy --strict src/ && pytest -q` from a clean clone — all must exit 0.
