# Phase 10.6 · Task 07 — Editable search config in the settings page

## Objective
Turn the read-only settings page into an editable form for the search config, so
each user can select what kind of offers to look for (roles, sectors, seniority,
location, min salary) without touching YAML by hand. Backed by Task 06's API.

## Acceptance criteria
- [x] `dashboard/src/app/[username]/settings/page.tsx` renders an editable form
      populated from `GET /users/{username}/search-config`, with inputs for:
      `target_roles` (add/remove list), `target_sectors` (add/remove list),
      `experience_level` (select: junior / mid / senior), `location_preference`
      (modality select + cities list), `min_salary` (number, optional).
      _`SearchConfigForm` client component fed by server-fetched `getSearchConfig`;
      `ListInput` chip+add for roles/sectors/cities._
- [x] Save calls `PUT /users/{username}/search-config`; success + validation-error
      (422) states are surfaced (toast via existing `ui/sonner`). On 422 the form
      keeps the user's input and shows the field error; nothing is silently lost.
      _`putSearchConfig` → success/error `toast`; on error local state is retained
      (no reset), 422 body shown in the toast message._
- [x] Non-editable profile data (CV, experiences, education) is **not** shown as
      editable here — at most read-only, matching the API's editable allow-list.
      _Personal data / stack / languages / red flags / CV / experiences / education
      / certs remain read-only `Section`s below the form._
- [x] Client-side guard rails mirror the server: `target_roles` cannot be emptied,
      `min_salary` must be positive or blank, `experience_level` constrained to the
      three values.
      _Empty-roles + non-positive-salary guarded before PUT; experience/modality are
      `<select>` constrained to valid values._
- [x] Mobile-friendly, dark-mode consistent with the rest of the dashboard. No
      TypeScript errors for touched files.
      _Reuses shadcn `Card`/`Input`/`Button`/`Badge`; `pnpm tsc --noEmit` + `pnpm
      lint` clean._

## Post-task extension (2026-06-13, user request)
Scope widened from the search-config subset to **full profile editing**: every
field is editable and erasable except `username` (locked — it is the YAML file
name + `users` PK + offer FK; renaming is a separate, riskier task).
- API: added `PUT /users/{username}/profile` (full `UserProfile`, validated,
  atomic write, username forced to the path). `GET /profile` unchanged.
- UI: `ProfileForm` (full editor with array editors for experiences / education /
  certifications) replaces `SearchConfigForm` in the settings page;
  `search-config-form.tsx` removed. The `GET/PUT /search-config` API endpoints +
  tests remain as a narrow programmatic surface.
- Tests: 4 added in `test_api_search_config.py` (round-trip + erase, username
  lock, invalid email 422, 404). `email`/`nombre`/`location` are required by
  validation, so they can be changed but not blanked.

## Implementation notes
- Today the page renders the raw YAML JSON from `GET /users/{username}/profile`
  (read-only). Replace that with the structured form bound to the new
  search-config endpoints.
- Reuse existing shadcn/ui primitives (`input`, `button`, `select`/`tabs`,
  `sonner`). List inputs (roles/sectors/cities) can be a simple chip+add pattern.
- Keep the per-user route (`[username]`) — edits target the selected user only.

## Files to create / modify
- `dashboard/src/app/[username]/settings/page.tsx`
- `dashboard/src/components/search-config-form.tsx` (new) + any small list-input
  component
- dashboard API client helper (add search-config GET/PUT)

## Dependencies
- Task 06 (search-config API).

## Estimated effort
**M**

## Testing notes
Manual: load settings for each user, change roles + experience_level + min_salary,
save, confirm the YAML updated (and a subsequent scrape uses the new config). Bad
input (empty roles) → server 422 surfaced, file unchanged. Optional Playwright
happy-path.
