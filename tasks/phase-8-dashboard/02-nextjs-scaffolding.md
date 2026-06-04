# Phase 8 · Task 02 — Next.js scaffolding (shadcn, Tailwind, dark mode)

## Objective
Bootstrap the Next.js 14 App Router app under `dashboard/` with the agreed UI stack.

## Acceptance criteria
- [x] `dashboard/` initialized with `pnpm create next-app` (TypeScript, App Router, Tailwind, ESLint, `src/` dir).
- [x] shadcn/ui installed and configured. Add at least: Button, Card, Input, Textarea, Badge, Table, Tabs, Sheet, Toast (sonner).
- [x] Dark mode default via `next-themes` (forced dark on first paint, no flash).
- [x] Tailwind config tweaked for our color palette (neutral/zinc base).
- [x] A `lib/api.ts` typed client wrapping `fetch` to the FastAPI base URL from `NEXT_PUBLIC_API_URL`.
- [x] Layout: top bar with current user selector + theme toggle, sidebar nav with v1 pages.
- [x] Mobile-friendly: nav collapses, key tables become cards under `md`.
- [x] `pnpm dev` runs cleanly.

## Files to create / modify
- Everything under `dashboard/`

## Dependencies
- Phase 8 / Task 01 (so the API exists to point at)

## Estimated effort
**L**

## Testing notes
Smoke check by opening `pnpm dev`. No automated tests required at this stage; subsequent page tasks add behavior worth testing.
