"""Azure OpenAI service wrapper: retries, prompt caching, and structured outputs."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from openai import APIStatusError, AsyncAzureOpenAI, RateLimitError
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel

from src.config import get_settings
from src.exceptions import JobAgentError

logger = structlog.get_logger(__name__)

_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({500, 502, 503, 504})
_MAX_RETRIES: int = 3
_BASE_BACKOFF_SECONDS: float = 1.0


class LLMError(JobAgentError):
    """Raised when all retry attempts for an LLM call are exhausted."""


@dataclass
class TokenUsage:
    """Token usage breakdown for a single LLM call."""

    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatResult:
    """Result of a single chat completion request."""

    content: str
    parsed: BaseModel | None
    usage: TokenUsage
    latency_ms: float
    model: str


@dataclass
class _RawResult:
    content: str
    parsed: BaseModel | None
    model: str
    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    total_tokens: int


UsageTrackerFn = Callable[[str, TokenUsage], None]
_usage_tracker: UsageTrackerFn | None = None


def register_usage_tracker(fn: UsageTrackerFn) -> None:
    """Register a callback invoked after every LLM call with the deployment name and usage.

    Phase 7 plugs into this to record token spend per run.

    Args:
        fn: Callable that receives the model name and ``TokenUsage``.
    """
    global _usage_tracker
    _usage_tracker = fn


class AzureOpenAIClient:
    """Single point of contact for all Azure OpenAI calls.

    Centralises retries, token accounting, and structured-output parsing.

    Prompt caching is handled automatically by Azure OpenAI when the system
    message is >= 1024 tokens and reused verbatim across calls.  The
    ``cacheable_system`` flag on ``chat()`` is informational only — it documents
    intent and will be used if the API ever exposes an explicit cache-control
    header.  Cached tokens are always reflected in ``ChatResult.usage.cached_tokens``.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            max_retries=0,  # custom retry logic below
        )
        self._deployments: dict[str, str] = {
            "mini": settings.azure_openai_deployment_mini,
            "4o": settings.azure_openai_deployment_4o,
        }

    def _resolve_deployment(self, key: Literal["mini", "4o"]) -> str:
        return self._deployments[key]

    async def _call_api(
        self,
        *,
        model: str,
        system: str,
        user: str,
        response_format: type[BaseModel] | None,
        extra: dict[str, Any],
    ) -> _RawResult:
        """Execute a single (non-retried) API call.

        Args:
            model: Resolved Azure deployment name.
            system: System prompt content.
            user: User turn content.
            response_format: Pydantic model for structured outputs, or ``None``.
            extra: Additional kwargs forwarded to the SDK.

        Returns:
            ``_RawResult`` with the raw response fields extracted.
        """
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system),
            ChatCompletionUserMessageParam(role="user", content=user),
        ]

        if response_format is not None:
            raw = await self._client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_format,
                **extra,
            )
            content = raw.choices[0].message.content or ""
            parsed: BaseModel | None = raw.choices[0].message.parsed
            completion_model = raw.model
            usage_raw = raw.usage
        else:
            raw2 = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                **extra,
            )
            content = raw2.choices[0].message.content or ""
            parsed = None
            completion_model = raw2.model
            usage_raw = raw2.usage

        prompt_tokens = usage_raw.prompt_tokens if usage_raw else 0
        completion_tokens = usage_raw.completion_tokens if usage_raw else 0
        total_tokens = usage_raw.total_tokens if usage_raw else 0
        cached_tokens = 0
        if usage_raw is not None:
            details = getattr(usage_raw, "prompt_tokens_details", None)
            if details is not None:
                cached_tokens = getattr(details, "cached_tokens", None) or 0

        return _RawResult(
            content=content,
            parsed=parsed,
            model=completion_model,
            prompt_tokens=prompt_tokens,
            cached_tokens=cached_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def chat(
        self,
        *,
        deployment: Literal["mini", "4o"],
        system: str,
        user: str,
        response_format: type[BaseModel] | None = None,
        cacheable_system: bool = True,
        **kwargs: Any,
    ) -> ChatResult:
        """Send a chat-completion request with retries and return a structured result.

        Args:
            deployment: ``"mini"`` for gpt-4o-mini, ``"4o"`` for gpt-4o.
            system: System prompt.  Azure caches automatically when this content
                is stable and >= 1024 tokens.  Put stable content first.
            user: User-turn content.
            response_format: Pydantic model class for structured outputs, or
                ``None`` for plain text.
            cacheable_system: Informational flag marking that ``system`` is stable
                and benefits from caching (no runtime effect; reserved for future
                explicit cache-control support).
            **kwargs: Extra keyword arguments forwarded to the underlying SDK call.

        Returns:
            ``ChatResult`` with content, optional parsed model, token usage, and
            wall-clock latency.

        Raises:
            LLMError: When all ``_MAX_RETRIES`` attempts fail.
        """
        _ = cacheable_system  # reserved for future explicit cache-control

        model = self._resolve_deployment(deployment)
        start = time.monotonic()
        last_exc: Exception | None = None
        raw: _RawResult | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                raw = await self._call_api(
                    model=model,
                    system=system,
                    user=user,
                    response_format=response_format,
                    extra=dict(kwargs),
                )
                break
            except RateLimitError as exc:
                last_exc = exc
                logger.warning(
                    "llm_rate_limit",
                    attempt=attempt,
                    deployment=deployment,
                )
            except APIStatusError as exc:
                if exc.status_code not in _RETRYABLE_STATUS_CODES:
                    raise LLMError(f"Non-retryable API error (HTTP {exc.status_code})") from exc
                last_exc = exc
                logger.warning(
                    "llm_server_error",
                    status=exc.status_code,
                    attempt=attempt,
                    deployment=deployment,
                )

            if attempt < _MAX_RETRIES - 1:
                wait = _BASE_BACKOFF_SECONDS * (2**attempt)
                await asyncio.sleep(wait)

        if raw is None:
            raise LLMError("LLM call failed after all retry attempts") from last_exc

        latency_ms = (time.monotonic() - start) * 1000

        usage = TokenUsage(
            prompt_tokens=raw.prompt_tokens,
            cached_tokens=raw.cached_tokens,
            completion_tokens=raw.completion_tokens,
            total_tokens=raw.total_tokens,
        )

        if _usage_tracker is not None:
            _usage_tracker(raw.model, usage)

        logger.debug(
            "llm_call_done",
            deployment=deployment,
            model=raw.model,
            prompt_tokens=raw.prompt_tokens,
            cached_tokens=raw.cached_tokens,
            completion_tokens=raw.completion_tokens,
            latency_ms=round(latency_ms, 1),
        )

        return ChatResult(
            content=raw.content,
            parsed=raw.parsed,
            usage=usage,
            latency_ms=latency_ms,
            model=raw.model,
        )
