# Phase EXTRA · Task 04 — GitHub Release v1.0.0

> ⚠️ **EXTRA / OPTIONAL phase.** Run only if/when going public. This is the task
> that was deferred from Phase 10 / Task 05.

## Objective
Publish a GitHub Release on the existing `v1.0.0` tag as a portfolio milestone.

## Acceptance criteria
- [ ] Release created on the **existing** annotated tag `v1.0.0` (do NOT create a
  new tag — it is already on origin at `ba9ec1d`).
- [ ] Title: `v1.0.0 — Flow B end-to-end`.
- [ ] Body = `docs/architecture.md` "Visión general" section + embedded dashboard
  screenshots. Once the repo is public, raw URLs pinned to the tag work:
  `https://raw.githubusercontent.com/JorgePulgar/Job-Application-Multi-Agent-System/v1.0.0/docs/screenshots/<file>.png`
  (drag-and-drop upload also fine).
- [ ] Verify the published page: 5 screenshots load, mermaid renders (if it shows
  as a raw code block, swap to a static PNG).
- [ ] Mark Phase 10 / Task 05 as fully complete (this closes the original deferral).

## Implementation notes
- Web UI: Releases → Draft new → choose tag `v1.0.0` → paste body → Publish.
- CLI (after `gh` installed): `gh release create v1.0.0 --title "..." --notes-file <body.md>`.
- Regenerate the body file on demand; it was intentionally not committed.

## Files to create / modify
- (None committed — release is a GitHub-side artifact)

## Dependencies
- Task 03 (README/screenshots ready), Task 05 below (repo public so raw URLs resolve)
  — or do drag-and-drop and run before going public.

## Estimated effort
**S**

## Testing notes
Load the release page logged-out; confirm images render.
