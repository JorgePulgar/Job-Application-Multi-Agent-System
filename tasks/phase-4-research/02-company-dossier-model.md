# Phase 4 · Task 02 — CompanyDossier Pydantic model

## Objective
Structured output of `CompanyResearcher`, persisted to `companies.dossier_completo` and used downstream by the evaluator and writer.

## Acceptance criteria
- [x] `src/models/company.py` defines `CompanyDossier` with at minimum: `sector`, `tamano` (enum: `startup|pyme|grande|enterprise|unknown`), `ubicacion_hq`, `descripcion`, `stack_tecnologico: list[str]`, `cultura_notas: list[str]`, `red_flags_detectadas: list[str]`, `productos_o_servicios: list[str]`, `equipo_ai_detectado: bool`, `fuentes: list[HttpUrl]`.
- [x] All fields documented. Validators ensure lists are deduplicated, lowercased where appropriate.
- [x] Helper `to_summary_for_prompt()` returns a concise markdown summary (≤ ~300 tokens) for inclusion in downstream prompts.

## Files to create / modify
- `src/models/company.py`
- `tests/unit/test_company_dossier.py`

## Dependencies
- Phase 1 complete

## Estimated effort
**S**

## Testing notes
Round-trip a sample dossier through JSON. Verify summary fits target length.
