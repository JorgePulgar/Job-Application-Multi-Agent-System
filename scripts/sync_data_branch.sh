#!/usr/bin/env bash
#
# Persist the runtime data (SQLite DB + generated drafts) on a dedicated `data`
# branch, separate from code history. Used by the daily-run GitHub Actions
# workflow (Phase 9 / Task 02, Option A).
#
# Usage:
#   scripts/sync_data_branch.sh pull   # restore data branch -> data/ before a run
#   scripts/sync_data_branch.sh push   # commit + push data/ -> data branch after a run
#
# A linked worktree at .databranch/ holds the `data` branch so the primary
# (code) working tree is never touched.

set -euo pipefail

BRANCH="data"
WT=".databranch"
PAYLOAD=("state.db" "drafts")

copy_into() {
  # copy_into <dest_dir>: mirror data/ payload into <dest_dir>
  local dest="$1"
  mkdir -p "$dest"
  if [ -f "data/state.db" ]; then
    cp -f "data/state.db" "$dest/state.db"
  fi
  rm -rf "${dest:?}/drafts"
  if [ -d "data/drafts" ]; then
    cp -rf "data/drafts" "$dest/drafts"
  fi
}

copy_from() {
  # copy_from <src_dir>: mirror <src_dir> payload back into data/
  local src="$1"
  mkdir -p "data/drafts"
  if [ -f "$src/state.db" ]; then
    cp -f "$src/state.db" "data/state.db"
  fi
  if [ -d "$src/drafts" ]; then
    rm -rf "data/drafts"
    cp -rf "$src/drafts" "data/drafts"
  fi
}

cmd_pull() {
  git fetch origin "$BRANCH" 2>/dev/null || true
  git worktree remove --force "$WT" 2>/dev/null || true

  if git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" >/dev/null 2>&1; then
    git worktree add -f -B "$BRANCH" "$WT" "origin/$BRANCH"
    copy_from "$WT"
    echo "Restored data from origin/$BRANCH."
  else
    # First run: create an empty orphan data branch in the worktree.
    git worktree add -f --detach "$WT"
    git -C "$WT" checkout --orphan "$BRANCH"
    git -C "$WT" rm -rf . >/dev/null 2>&1 || true
    echo "No '$BRANCH' branch yet — starting fresh."
  fi
}

cmd_push() {
  if [ ! -d "$WT" ]; then
    # pull was not run (or worktree gone) — recreate it.
    cmd_pull
  fi

  copy_into "$WT"
  git -C "$WT" add -A

  if git -C "$WT" diff --cached --quiet; then
    echo "No data changes to push."
    return 0
  fi

  git -C "$WT" \
    -c user.name="job-agent-bot" \
    -c user.email="job-agent-bot@users.noreply.github.com" \
    commit -m "data: run $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git -C "$WT" push origin "HEAD:$BRANCH"
  echo "Pushed data to origin/$BRANCH."
}

case "${1:-}" in
  pull) cmd_pull ;;
  push) cmd_push ;;
  *)
    echo "Usage: $0 {pull|push}" >&2
    exit 2
    ;;
esac
