# Phase 6 · Task 01 — Draft Pydantic model

## Objective
Schema for application drafts (subject + email body + cover letter), persisted to `drafts`.

## Acceptance criteria
- [ ] `src/models/draft.py` defines `Draft`: `email_subject: str` (≤120 chars), `email_body: str` (markdown), `carta_presentacion: str` (markdown, optional), `experiencias_destacadas: list[str]` (3-5 bullets), `needs_manual_context: bool = False`, `flagged_reasons: list[str]`.
- [ ] Validators: subject non-empty when `needs_manual_context=False`; body min length 200 chars when `needs_manual_context=False`.
- [ ] Helper `to_db_row(offer_id: int, user_id: int) -> db.Draft`.

## Files to create / modify
- `src/models/draft.py`
- `tests/unit/test_draft_model.py`

## Dependencies
- Phase 1 complete

## Estimated effort
**S**

## Testing notes
Test that an empty subject is rejected when not flagged, but accepted when `needs_manual_context=True`.
