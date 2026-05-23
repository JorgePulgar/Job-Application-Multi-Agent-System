# Job Application Multi-Agent System

Automated job hunting assistant for AI / data / engineering roles in Spain.

## Setup

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# or on Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install dependencies

```bash
uv sync --extra dev
```

### 3. Configure environment

```bash
cp .env.example .env
# Fill in the required API keys — see .env.example for descriptions
```

### 4. Initialise the database

```bash
uv run python -m src.cli db init
```

### 5. Load user profiles

```bash
cp config/users/jorge.yaml.example config/users/jorge.yaml
# Edit jorge.yaml with real details
uv run python -m src.cli profile load --user jorge
```

## Running tests

```bash
uv run pytest -q
```

## Running quality checks

```bash
uv run ruff check src/ api/
uv run ruff format --check src/ api/
uv run mypy --strict src/ api/
```

## CLI reference

```
python -m src.cli --help
```
