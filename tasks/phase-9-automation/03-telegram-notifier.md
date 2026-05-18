# Phase 9 · Task 03 — Telegram notifier service + summary

## Objective
Send a summary message to Telegram at the end of every daily run.

## Acceptance criteria
- [ ] `src/services/telegram.py` exposes `async def send_message(text: str, *, parse_mode: str = "MarkdownV2") -> None`. Uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- [ ] On 429, respects `retry_after`. On other failures, logs and returns without raising (notifier failure must not fail the run).
- [ ] `Orchestrator.run_for_all_users` calls a `format_summary(results: list[RunResult]) -> str` and sends one message per workflow run.
- [ ] Summary per user: scrapeados, filtrados (relevantes vs descartados), researched, evaluados, drafts (incluyendo `needs_manual_context`), tokens, coste estimado EUR. Global totals at top.
- [ ] Summary uses MarkdownV2-safe escaping (helper inside `telegram.py`).

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
