# Phase 3 · Task 01 — Azure OpenAI client wrapper

## Objective
Single point of contact with Azure OpenAI. Every agent goes through this wrapper so we can centralize retries, token accounting, prompt caching, and prompt-template loading.

## Acceptance criteria
- [ ] `src/services/azure_openai.py` exposes `class AzureOpenAIClient` with:
  - `async def chat(*, deployment: Literal["mini", "4o"], system: str, user: str, response_format: Optional[type[BaseModel]] = None, cacheable_system: bool = True, **kwargs) -> ChatResult`
  - `ChatResult` is a dataclass with `content: str`, `parsed: Optional[BaseModel]`, `usage` (prompt/cached/completion tokens), `latency_ms`, `model`.
- [ ] Uses the official `openai` SDK with `AzureOpenAI` / `AsyncAzureOpenAI`, `api_version` from settings.
- [ ] Maps `deployment="mini"` → `AZURE_OPENAI_DEPLOYMENT_MINI`, `"4o"` → `AZURE_OPENAI_DEPLOYMENT_4O`.
- [ ] Enables prompt caching for stable system content (mark system message as cache-eligible via the SDK's caching mechanism for the API version in use).
- [ ] Retries: 3 attempts with exponential backoff on `RateLimitError` and 5xx; no retries on 4xx other than 429.
- [ ] When `response_format` is a Pydantic model, uses the SDK's structured outputs feature and returns the parsed object.
- [ ] All token usage forwarded to a `usage_tracker` (Phase 7 will plug into this; for now just expose the hook).

## Files to create / modify
- `src/services/azure_openai.py`
- `src/services/prompt_loader.py` (loads `src/prompts/*.md` with optional `{{var}}` interpolation)
- `tests/unit/test_azure_openai_client.py`

## Dependencies
- Phase 1 complete

## Estimated effort
**L**

## Testing notes
Mock the `openai` SDK at the client level. Verify deployment selection, retry behavior on synthetic 429, parsed output when `response_format` is set, and that usage info is captured.

> If the exact prompt-caching API for the selected `AZURE_OPENAI_API_VERSION` is unclear, look it up before writing code — do not invent SDK methods.
