# Phase 10 · Task 02 — docs/architecture.md

## Objective
A deeper architecture document for technical readers (and portfolio reviewers).

## Acceptance criteria
- [x] `docs/architecture.md` covers, in Spanish:
  - Visión general con diagrama de componentes (mermaid C4-ish).
  - Por qué multi-agent en lugar de un solo prompt (justificación de la división).
  - Decisiones de diseño clave: SQLite por simplicidad, sin RAG en v1, prompt caching, gpt-4o-mini vs gpt-4o, human-in-the-loop.
  - Anti-decisiones: por qué no hay vector DB, por qué no hay cold outreach en v1.
  - Cómo se persiste el estado entre runs.
  - Cómo se hace QA del output (lint + regen).
  - Cómo se manejan errores (per-offer try/except, run_logs).
  - Riesgos y mitigaciones (ToS, throttling, falsos positivos del filtro).
- [x] Optional `docs/architecture.en.md` brief English version.

## Files to create / modify
- `docs/architecture.md`
- `docs/architecture.en.md` (optional)

## Dependencies
- Phase 10 / Task 01

## Estimated effort
**M**

## Testing notes
Manual review. Diagrams render.
