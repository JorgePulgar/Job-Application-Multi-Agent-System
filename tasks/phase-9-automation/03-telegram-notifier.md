# Phase 9 · Task 03 — Telegram notifier service + summary

## Objective
Send a summary message to Telegram at the end of every daily run.

## Acceptance criteria
- [x] `src/services/telegram.py` exposes `async def send_message(text: str, *, parse_mode: str = "MarkdownV2") -> None`. Uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- [x] On 429, respects `retry_after`. On other failures, logs and returns without raising (notifier failure must not fail the run).
- [x] `Orchestrator.run_for_all_users` calls a `format_summary(results: list[RunResult]) -> str` and sends one message per workflow run.
- [x] Summary per user: scrapeados, filtrados (relevantes vs descartados), researched, evaluados, drafts (incluyendo `needs_manual_context`), tokens, coste estimado EUR. Global totals at top.
- [x] Summary uses MarkdownV2-safe escaping (helper inside `telegram.py`).

## Implementation notes
- Extended `RunResult` with `ofertas_descartadas`, `ofertas_investigadas`, `ofertas_evaluadas`, `drafts_manual_context`, populated by per-stage counters in `run_for_user`.
- `send_message` swallows all failures (incl. missing config) so the notifier can never break a run; one retry on 429 using `parameters.retry_after` (body) → `Retry-After` (header) → 1s.
- `format_summary` escapes all dynamic text via `escape_markdown_v2`; only the deliberate `*bold*` markers are unescaped.

## Files to create / modify
- `src/services/telegram.py`
- `src/orchestrator.py` (extend Phase 7)
- `tests/unit/test_telegram.py`

## Dependencies
- Phase 7 complete
- Phase 9 / Task 01

## Estimated effort
**M**

## Testing notes
`respx` to mock the Telegram API. Verify message body, escaping, and that a transport failure does NOT raise.
