"""Unit tests for src/services/azure_openai.py."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import APIStatusError, RateLimitError
from pydantic import BaseModel

from src.services.azure_openai import (
    AzureOpenAIClient,
    ChatResult,
    LLMError,
    TokenUsage,
    register_usage_tracker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
    "AZURE_OPENAI_KEY": "test-key-abc123",
    "AZURE_OPENAI_API_VERSION": "2024-10-21",
    "AZURE_OPENAI_DEPLOYMENT_MINI": "gpt-4o-mini",
    "AZURE_OPENAI_DEPLOYMENT_4O": "gpt-4o",
    "ADZUNA_APP_ID": "aid",
    "ADZUNA_APP_KEY": "akey",
    "JOOBLE_API_KEY": "jkey",
    "TELEGRAM_BOT_TOKEN": "1234:tok",
    "TELEGRAM_CHAT_ID": "9999",
}


def _fake_http_response(status: int = 429) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "https://test.com"))


def _make_raw_completion(
    content: str = "hello",
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 10,
    cached_tokens: int = 0,
    completion_tokens: int = 5,
) -> MagicMock:
    """Build a mock ChatCompletion-like object."""
    mock = MagicMock()
    mock.choices[0].message.content = content
    mock.model = model
    mock.usage.prompt_tokens = prompt_tokens
    mock.usage.completion_tokens = completion_tokens
    mock.usage.total_tokens = prompt_tokens + completion_tokens
    details = MagicMock()
    details.cached_tokens = cached_tokens
    mock.usage.prompt_tokens_details = details if cached_tokens else None
    return mock


def _make_parsed_completion(
    parsed_obj: BaseModel,
    content: str = "",
    model: str = "gpt-4o-mini",
) -> MagicMock:
    """Build a mock ParsedChatCompletion-like object."""
    mock = MagicMock()
    mock.choices[0].message.content = content
    mock.choices[0].message.parsed = parsed_obj
    mock.model = model
    mock.usage.prompt_tokens = 20
    mock.usage.completion_tokens = 15
    mock.usage.total_tokens = 35
    mock.usage.prompt_tokens_details = None
    return mock


class _Answer(BaseModel):
    answer: str
    score: int


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    from src.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, val in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, val)


@pytest.fixture()
def mock_async_client() -> MagicMock:
    """Return a MagicMock that stands in for AsyncAzureOpenAI."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    client.beta.chat.completions.parse = AsyncMock()
    return client


@pytest.fixture()
def llm(env: None, mock_async_client: MagicMock) -> AzureOpenAIClient:
    """Return an AzureOpenAIClient whose inner openai client is fully mocked."""
    with patch("src.services.azure_openai.AsyncAzureOpenAI", return_value=mock_async_client):
        return AzureOpenAIClient()


# ---------------------------------------------------------------------------
# Deployment selection
# ---------------------------------------------------------------------------


def test_resolves_mini_deployment(llm: AzureOpenAIClient) -> None:
    assert llm._resolve_deployment("mini") == "gpt-4o-mini"


def test_resolves_4o_deployment(llm: AzureOpenAIClient) -> None:
    assert llm._resolve_deployment("4o") == "gpt-4o"


# ---------------------------------------------------------------------------
# Successful plain-text call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plain_chat_returns_content(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    mock_async_client.chat.completions.create.return_value = _make_raw_completion("hola mundo")

    result = await llm.chat(deployment="mini", system="sys", user="usr")

    assert isinstance(result, ChatResult)
    assert result.content == "hola mundo"
    assert result.model == "gpt-4o-mini"
    assert result.parsed is None


# ---------------------------------------------------------------------------
# Structured outputs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structured_output_returns_parsed(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    expected = _Answer(answer="Madrid", score=9)
    mock_async_client.beta.chat.completions.parse.return_value = _make_parsed_completion(expected)

    result = await llm.chat(
        deployment="mini",
        system="sys",
        user="usr",
        response_format=_Answer,
    )

    assert isinstance(result.parsed, _Answer)
    assert result.parsed.answer == "Madrid"
    assert result.parsed.score == 9
    mock_async_client.beta.chat.completions.parse.assert_called_once()
    mock_async_client.chat.completions.create.assert_not_called()


# ---------------------------------------------------------------------------
# Token usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usage_fields_populated(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    mock_async_client.chat.completions.create.return_value = _make_raw_completion(
        prompt_tokens=100,
        cached_tokens=80,
        completion_tokens=20,
    )

    result = await llm.chat(deployment="mini", system="sys", user="usr")

    assert result.usage.prompt_tokens == 100
    assert result.usage.cached_tokens == 80
    assert result.usage.completion_tokens == 20
    assert result.usage.total_tokens == 120


@pytest.mark.asyncio
async def test_usage_tracker_called(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    mock_async_client.chat.completions.create.return_value = _make_raw_completion(
        prompt_tokens=50, completion_tokens=10
    )
    received: list[tuple[str, TokenUsage]] = []

    register_usage_tracker(lambda model, usage: received.append((model, usage)))
    try:
        await llm.chat(deployment="mini", system="sys", user="usr")
    finally:
        register_usage_tracker(lambda *_: None)  # reset

    assert len(received) == 1
    assert received[0][0] == "gpt-4o-mini"
    assert received[0][1].prompt_tokens == 50


# ---------------------------------------------------------------------------
# Retry on 429
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_rate_limit(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    rate_err = RateLimitError("rate limited", response=_fake_http_response(429), body=None)
    success = _make_raw_completion("ok")

    mock_async_client.chat.completions.create.side_effect = [rate_err, success]

    with patch("src.services.azure_openai.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        result = await llm.chat(deployment="mini", system="sys", user="usr")

    assert result.content == "ok"
    assert mock_async_client.chat.completions.create.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_raises_llm_error_after_all_retries(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    rate_err = RateLimitError("rate limited", response=_fake_http_response(429), body=None)
    mock_async_client.chat.completions.create.side_effect = rate_err

    with patch("src.services.azure_openai.asyncio.sleep", new=AsyncMock()), pytest.raises(LLMError):
        await llm.chat(deployment="mini", system="sys", user="usr")

    assert mock_async_client.chat.completions.create.call_count == 3


# ---------------------------------------------------------------------------
# Retry on 5xx — no retry on 4xx other than 429
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_500(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    err_500 = APIStatusError("server error", response=_fake_http_response(500), body=None)
    success = _make_raw_completion("recovered")

    mock_async_client.chat.completions.create.side_effect = [err_500, success]

    with patch("src.services.azure_openai.asyncio.sleep", new=AsyncMock()):
        result = await llm.chat(deployment="mini", system="sys", user="usr")

    assert result.content == "recovered"
    assert mock_async_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_no_retry_on_400(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    err_400 = APIStatusError("bad request", response=_fake_http_response(400), body=None)
    mock_async_client.chat.completions.create.side_effect = err_400

    with pytest.raises(LLMError, match="400"):
        await llm.chat(deployment="mini", system="sys", user="usr")

    # Only called once — no retries on non-retryable 4xx
    assert mock_async_client.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# Latency field is populated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_latency_ms_is_positive(
    llm: AzureOpenAIClient,
    mock_async_client: MagicMock,
) -> None:
    mock_async_client.chat.completions.create.return_value = _make_raw_completion()
    result = await llm.chat(deployment="mini", system="sys", user="usr")
    assert result.latency_ms >= 0
