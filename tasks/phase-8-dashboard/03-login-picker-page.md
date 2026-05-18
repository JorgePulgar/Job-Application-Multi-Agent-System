# Phase 8 · Task 03 — `/` login picker page

## Objective
Landing page with one button per user. No real auth in v1.

## Acceptance criteria
- [ ] `app/page.tsx` fetches `GET /users` and renders one big card/button per user with their display name.
- [ ] Selecting a user stores `username` in localStorage and redirects to `/drafts`.
- [ ] Top-bar user selector reflects the choice on every subsequent page.
- [ ] Loading and empty states handled gracefully.

## Files to create / modify
- `dashboard/src/app/page.tsx`
- `dashboard/src/components/user-picker.tsx`
- `dashboard/src/lib/user.ts` (current-user hook)

## Dependencies
- Phase 8 / Tasks 01, 02

## Estimated effort
**S**

## Testing notes
Manual smoke test. Optional: a Playwright component test for the picker.
