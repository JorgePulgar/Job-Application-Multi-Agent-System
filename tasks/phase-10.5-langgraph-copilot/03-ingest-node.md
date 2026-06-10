# Phase 10.5 · Task 03 — ingest_offer node

## Objective
Parse the offer (DB row, pasted text, or URL) into a structured `ParsedOffer`.

## Acceptance criteria
- [x] `src/graph/nodes/ingest.py` implements `async def ingest_offer(state) -> dict`
      returning `{"parsed": ParsedOffer}`. _Built by `make_ingest_offer(client,
      session_factory)` factory (DI via closure; deps not in node signature)._
- [x] Loads the `Offer` row by `state["offer_id"]`; uses `descripcion` + `raw_json`.
      If a URL-only source is supported later, fetch via the existing web/http
      service — never a new client.
- [x] Uses `gpt-4o-mini` (cheap, mechanical extraction) with
      `response_format=ParsedOffer`, `cacheable_system=True`.
- [x] Detects offer language → `ParsedOffer.detected_language` (`es`/`en`). This
      value drives the language of every downstream node + the final draft.
- [x] Prompt in `src/prompts/graph_ingest.{system,user}.md`.
- [x] Missing fields → `None`/empty, **never invented** (rubric: "not stated").
- [x] Node calls `AzureOpenAIClient` from `src/services` — no inline LLM call.

## Files to create / modify
- `src/graph/nodes/__init__.py`
- `src/graph/nodes/ingest.py`
- `src/prompts/graph_ingest.system.md`
- `src/prompts/graph_ingest.user.md`
- `tests/unit/test_node_ingest.py`

## Dependencies
- Task 02.

## Estimated effort
**M**

## Testing notes
Mock the LLM client; assert a JD with no salary yields `salary_raw=None` and a
populated `required_skills`. Assert an English JD yields `detected_language="en"`
and a Spanish JD yields `"es"`.
