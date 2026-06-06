# Operations

Operational notes for running and maintaining the Job Application Multi-Agent
System in production (GitHub Actions).

## ⚠️ Pending manual verification (Phase 9)

Phase 9 (automation) is code-complete and tested in CI/unit, but **not yet
verified live** — it needs real credentials. Before relying on the daily
automation, do this once:

1. Add the 12 secrets from CLAUDE.md §5 in **Settings → Secrets and variables
   → Actions** (incl. `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
2. **Actions → daily-run → Run workflow**, first with the **Dry run** box
   ticked, then a real run.
3. Confirm: the workflow goes green, a **`data`** branch appears holding
   `state.db`, and a Telegram **run summary** message arrives (plus a cost
   alert only if the run cost exceeds `DAILY_COST_ALERT_EUR`).

Until this is done, the scheduled run will fail (missing secrets / no user
profiles on CI).

## Runtime data persistence (the `data` branch)

The daily run is stateful: it builds on the previous day's SQLite database and
generated drafts. GitHub Actions runners are ephemeral, so the runtime data is
persisted on a dedicated **`data` branch** (Phase 9 / Task 02, Option A).

What lives on the `data` branch:

- `state.db` — the SQLite database.
- `drafts/` — generated draft artifacts.

This branch contains **only** runtime data, never code. It never contains
secrets (`.env` is gitignored) or user profiles (`config/users/*.yaml` are
gitignored). The database holds the user's own application content and public
company/offer data — no third-party credentials.

### How the workflow uses it

`scripts/sync_data_branch.sh` drives this via a linked worktree at
`.databranch/` so the code working tree is never disturbed:

1. **pull** (before the run): fetch `origin/data`, check it out into
   `.databranch/`, and copy `state.db` + `drafts/` into `data/`. On the very
   first run (no `data` branch yet) it starts from an empty orphan branch.
2. The pipeline runs and writes to `data/`.
3. **push** (after the run, even on failure; skipped on dry runs): copy `data/`
   back into the worktree, commit, and push to `origin/data`. No commit is made
   if nothing changed.

## Recovery procedures

### Refresh local data from production

To view the latest production data in your local dashboard:

```bash
git fetch origin data
# Inspect or extract the latest DB without switching your branch:
git show origin/data:state.db > data/state.db
# (and, if needed, the drafts)
rm -rf data/drafts && git --work-tree=. checkout origin/data -- drafts 2>/dev/null || true
```

Then start the API (`uv run uvicorn api.main:app --reload`) — it reads
`data/state.db`.

### Rebuild from scratch (lost or corrupted `data` branch)

The data branch is regenerable; nothing irreplaceable lives only there.

```bash
# 1. Recreate an empty database with the current schema.
uv run python -m src.cli db init        # alembic upgrade head

# 2. Reload user profiles into the users table.
uv run python -m src.cli profile load --user jorge
uv run python -m src.cli profile load --user madalina

# 3. Let the next scheduled (or manual) run repopulate offers/drafts.
```

To discard a corrupted `data` branch and let the workflow recreate it, delete
the branch on the remote; the next run starts from a fresh orphan branch:

```bash
git push origin --delete data
```

### First-run / manual trigger

Use the **Actions → daily-run → Run workflow** button. Tick **Dry run** to
exercise the pipeline logic without writing to the DB or pushing data.

## Secrets

All credentials come from GitHub repo secrets (Settings → Secrets and variables
→ Actions), mapped to env in `daily-run.yml`. See CLAUDE.md §5 for the full
list. Never commit `.env` or `config/users/*.yaml`.
