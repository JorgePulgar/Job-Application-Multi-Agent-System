# Phase 10 · Task 01 — Bilingual README + mermaid architecture diagram

## Objective
Replace the stub README with a polished bilingual one (Spanish primary, English secondary).

## Acceptance criteria
- [x] `README.md` (Spanish, primary):
  - Hero blurb (1-2 paragraphs) explaining what the system does, for whom, and the human-in-the-loop principle.
  - Tabla de contenidos.
  - Arquitectura (mermaid diagram of the pipeline: scrape → filter → research → evaluate → write → dashboard → user → applications).
  - Stack tecnológico (bullet list).
  - Cómo arrancar localmente (env, uv, alembic, ejecutar orquestador, levantar dashboard + API).
  - Cómo añadir un nuevo usuario (YAML + `profile load`).
  - Cómo funciona el scheduling (resumen del workflow).
  - Coste estimado (rango realista por día).
  - Limitaciones y alcance (lista explícita: Flow A out of scope; LinkedIn no se scrapea; el sistema nunca envía).
  - Licencia / contacto.
- [x] `README.en.md` (English mirror, slightly more concise).
- [x] Link from `README.md` to `README.en.md` at top.
- [x] Both files lint-clean (no broken links).

## Implementation notes
- Verified all internal links resolve (READMEs, dashboard/api docs, operations.md, workflow, yaml.example, .env.example).
- Mermaid pipeline diagram includes the Telegram summary edge. Quoted node labels so the `·` separators render on GitHub.
- No LICENSE file exists → stated "personal/portfolio, ask before reusing"; contact = Jorge / jpulgar111@gmail.com.

## Files to create / modify
- `README.md`
- `README.en.md`

## Dependencies
- Phases 1-9 complete

## Estimated effort
**M**

## Testing notes
Manual review. Verify mermaid renders correctly on GitHub.
