# Phase 2 · Task 02 — JobOffer Pydantic model

## Objective
Pydantic model that every scraper returns, decoupled from the SQLAlchemy `Offer` table.

## Acceptance criteria
- [ ] `src/models/job_offer.py` defines `JobOffer` with: `titulo`, `empresa`, `ubicacion`, `modalidad` (enum: `remote|hybrid|onsite|unknown`), `salario_min: Optional[int]`, `salario_max: Optional[int]`, `descripcion: str`, `url`, `plataforma`, `fecha_publicacion: Optional[date]`.
- [ ] `hash_unico` is a `@computed_field` over normalized `titulo + empresa + ubicacion` (sha256). Normalization: lowercase, NFKD, strip punctuation, collapse whitespace.
- [ ] Converter `to_db_offer(user_id: int, company_id: int) -> db.Offer` in same file (or a `db_mappers.py`).
- [ ] All fields documented with Google-style docstrings.

## Files to create / modify
- `src/models/job_offer.py`
- `tests/unit/test_job_offer_model.py`

## Dependencies
- Phase 1 complete

## Estimated effort
**S**

## Testing notes
Test that two offers with the same titulo/empresa/ubicacion (different casing, accents) produce the same `hash_unico`. Test conversion to `db.Offer` populates the expected columns.
