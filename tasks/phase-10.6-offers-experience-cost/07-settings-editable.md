# Phase 10.6 · Task 07 — Editable search config in the settings page

## Objective
Turn the read-only settings page into an editable form for the search config, so
each user can select what kind of offers to look for (roles, sectors, seniority,
location, min salary) without touching YAML by hand. Backed by Task 06's API.

## Acceptance criteria
- [ ] `dashboard/src/app/[username]/settings/page.tsx` renders an editable form
      populated from `GET /users/{username}/search-config`, with inputs for:
      `target_roles` (add/remove list), `target_sectors` (add/remove list),
      `experience_level` (select: junior / mid / senior), `location_preference`
      (modality select + cities list), `min_salary` (number, optional).
- [ ] Save calls `PUT /users/{username}/search-config`; success + validation-error
      (422) states are surfaced (toast via existing `ui/sonner`). On 422 the form
      keeps the user's input and shows the field error; nothing is silently lost.
- [ ] Non-editable profile data (CV, experiences, education) is **not** shown as
      editable here — at most read-only, matching the API's editable allow-list.
- [ ] Client-side guard rails mirror the server: `target_roles` cannot be emptied,
      `min_salary` must be positive or blank, `experience_level` constrained to the
      three values.
- [ ] Mobile-friendly, dark-mode consistent with the rest of the dashboard. No
      TypeScript errors for touched files.

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
