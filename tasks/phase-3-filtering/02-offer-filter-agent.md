# Phase 3 · Task 02 — OfferFilter agent

## Objective
For every `new` offer, decide `relevant | discarded` and write a short reason if discarded. Uses `gpt-4o-mini` for cost reasons.

## Acceptance criteria
- [x] `src/agents/offer_filter.py` implements `class OfferFilter` with `async def evaluate(self, offer: db.Offer, profile: UserProfile) -> FilterDecision`.
- [x] `FilterDecision` Pydantic model: `relevant: bool`, `razon_descarte: Optional[str]` (≤ 200 chars).
- [x] Uses structured outputs (`response_format=FilterDecision`).
- [x] Pre-LLM cheap pass: if any `profile.red_flags` substring matches the offer's `descripcion` (case-insensitive), discard immediately without an LLM call.
- [x] Updates the offer row: `estado = 'relevant'` or `'discarded'`, set `razon_descarte` if discarded.
- [x] Batched: caller can pass a list and the agent processes them sequentially (no concurrency from inside; orchestrator decides parallelism).

## Files to create / modify
- `src/agents/offer_filter.py`
- `src/models/decisions.py` (or extend `src/models/`)
- `tests/unit/test_offer_filter.py`

## Dependencies
- Phase 3 / Task 01
- Phase 3 / Task 03

## Estimated effort
**M**

## Testing notes
Mock `AzureOpenAIClient.chat` to return canned `FilterDecision`. Test: red-flag short-circuit skips the LLM; relevant + discarded both update the DB correctly.
