# Phase 10 · Task 03 — Dashboard screenshots

## Objective
Visual portfolio material for the dashboard.

## Acceptance criteria
- [x] `docs/screenshots/` contains PNGs for: `/`, `/drafts` (list), `/drafts/[id]` (detail with sample draft), `/history`, `/settings`. All dark mode.
- [x] Each screenshot uses fabricated example data only (no real personal data, no real companies you've actually applied to).
- [x] README and `docs/architecture.md` embed selected screenshots.

## Implementation notes
- Captured via Playwright (project dep) against the local dashboard at 1366×900, `color_scheme=dark`, 2× DPI. Temp capture script was not committed.
- Data is fabricated (NeuralForge / DataPyme, Jorge/Madalina example profiles, Acme Fintech experiences) — from the committed `*.example` profiles + `scripts/seed_demo.py`.
- Embedded drafts/detail/history in README.md, drafts/detail in README.en.md, detail in docs/architecture.md.

## Files to create / modify
- `docs/screenshots/*.png`
- `README.md` (embed)
- `docs/architecture.md` (embed where relevant)

## Dependencies
- Phase 8 complete

## Estimated effort
**S**

## Testing notes
Verify the embedded images render on GitHub.
