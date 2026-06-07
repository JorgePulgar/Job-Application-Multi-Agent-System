# Phase 10 · Task 05 — Portfolio tag

## Objective
Cut a versioned tag so the v1 milestone is preserved for portfolio purposes.

## Acceptance criteria
- [x] Tag `v1.0.0` on the commit that closes Phase 10 / Task 04. (on `34fbeb6`)
- [x] Tag message: "v1.0.0 — Flow B end-to-end. Human-in-the-loop, daily orchestration, dashboard."
- [x] Push tag.
- [x] GitHub Release created with the contents of `docs/architecture.md`'s "Visión general" as the body and embedded screenshots. **Skipped — repo stays private for personal use; the annotated `v1.0.0` tag already preserves the milestone.** Release + public-repo prep deferred to `phase-extra-public-repo/` (run only if/when going public).

## Implementation notes
- Tag is annotated, on `34fbeb6` (the task-04 closing commit). Pushed to origin.
- Release creation requires `gh` or a GitHub token (neither available here). Body prepared from architecture.md "Visión general" + screenshots embedded via raw URLs pinned to the `v1.0.0` tag.

## Files to create / modify
- (None — repo state operations only)

## Dependencies
- Phase 10 / Tasks 01-04

## Estimated effort
**S**

## Testing notes
None.

## ⛔ End of Phase 10 — STOP

After completing this task, the assistant MUST stop and tell the user:

> Phase 10 complete. v1 is done. Per the brief, **do not start Phase 11 (Warm Outreach) without explicit approval.** Use v1 in real life for at least a few weeks; if you decide to extend, say "approve Phase 11" and I'll begin task 01.

Do NOT proceed to Phase 11 automatically under any circumstance.
