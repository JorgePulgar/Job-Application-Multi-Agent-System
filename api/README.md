# API (FastAPI)

Small read-mostly backend that serves the dashboard from the project SQLite
database. It exposes users, drafts (detail + edit + actions), history, and
profile endpoints.

## Run

From the **repo root** (the DB path is resolved relative to the working
directory):

```bash
uv run uvicorn api.main:app --reload
```

Serves on <http://localhost:8000>. Interactive docs at
<http://localhost:8000/docs>, liveness at `/health`.

The database must exist first — run `uv run python -m src.cli db init` and load
at least one profile (`uv run python -m src.cli profile load --user jorge`).
See the root [`README.md`](../README.md) for full setup.

## Database

- Location: `data/state.db` (SQLite), relative to the repo root.
- The API only reads/writes this file via SQLAlchemy; it never provisions it.
  Schema and migrations are owned by Alembic (`uv run alembic upgrade head`).

## Environment

| Variable        | Default                 | Purpose                                              |
| --------------- | ----------------------- | ---------------------------------------------------- |
| `CORS_ORIGINS`  | `http://localhost:3000` | Comma-separated allowed origins for the dashboard.   |
| `PROFILES_DIR`  | `config/users`          | Directory holding `<username>.yaml` profiles.        |

The `POST /drafts/{id}/regenerate` endpoint additionally calls Azure OpenAI, so
it needs the `AZURE_OPENAI_*` variables from `.env` (see `.env.example`). Every
other endpoint works without any external keys.

## Endpoints

| Method | Path                          | Purpose                          |
| ------ | ----------------------------- | -------------------------------- |
| GET    | `/users`                      | List configured users.           |
| GET    | `/users/{username}/drafts`    | Paginated, filterable drafts.    |
| GET    | `/users/{username}/history`   | Application history.             |
| GET    | `/users/{username}/profile`   | Raw YAML profile as JSON.        |
| GET    | `/drafts/{id}`                | Full draft detail.               |
| PATCH  | `/drafts/{id}`                | Edit subject / body / cover.     |
| POST   | `/drafts/{id}/mark-sent`      | Record a sent application.       |
| POST   | `/drafts/{id}/discard`        | Discard a draft.                 |
| POST   | `/drafts/{id}/regenerate`     | Regenerate via the writer agent. |
