# Phase 11 · Task 01 — Schema additions + Alembic migration

> **Phase 11 is locked behind explicit user approval after Phase 10.** Do not start without it.

## Objective
Add `outreach_targets` and `outreach_signals` tables, and a `priority_for_outreach` computed property on companies.

## Acceptance criteria
- [ ] `src/db/models.py` adds:
  - `OutreachTarget` with columns from CLAUDE.md §6 / v1.1: `company_id`, `user_id`, `nombre_persona`, `rol`, `linkedin_url`, `razon_eleccion`, `fuente_descubrimiento` (enum: `linkedin_search|company_web|github|other`), `contexto_personalizacion` (nullable), `fecha_encontrado`, `fecha_ultimo_signal_check`, `mensaje_borrador`, `estado` (enum: `draft|needs_manual_context|approved|sent|replied|no_reply|discarded`), `fecha_envio` (nullable), `respuesta_recibida`, `tipo_respuesta` (nullable), `notas`.
  - `OutreachSignal`: `target_id`, `tipo` (enum: `new_post|company_news|role_change|talk_published|other`), `descripcion`, `url` (nullable), `fecha_detectado`, `usado_en_mensaje`.
- [ ] `src/db/enums.py` extended with the new enums.
- [ ] `Company` gets a `@hybrid_property priority_for_outreach` derived from: best evaluation score for the company in `evaluations` JOIN `offers` ≥ threshold, `tamano ∈ {startup, pyme}`, and `equipo_ai_detectado=True` in dossier. Returns `bool` and a numeric priority score.
- [ ] Alembic migration created and applies cleanly on top of the v1 schema.
- [ ] Pydantic models for both new entities in `src/models/outreach.py`.

## Files to create / modify
- `src/db/models.py`
- `src/db/enums.py`
- `src/models/outreach.py`
- `alembic/versions/<hash>_phase11_outreach.py`
- `tests/unit/test_outreach_models.py`

## Dependencies
- Phase 10 approved + user explicit go-ahead for Phase 11

## Estimated effort
**M**

## Testing notes
Apply migration on a fresh DB and on an existing v1 DB. Verify `priority_for_outreach` returns true on a seeded high-score + small-company case.
