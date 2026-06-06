"""Telegram notification service.

Sends a single run-summary message at the end of each daily pipeline run. A
notifier failure must never fail the run, so transport errors are logged and
swallowed.
"""

from __future__ import annotations

import asyncio

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)

_API_BASE = "https://api.telegram.org"
_TIMEOUT = 15.0
_MAX_RETRIES = 1  # one retry, honouring Telegram's retry_after on HTTP 429

# Characters that MUST be backslash-escaped in Telegram MarkdownV2.
_MDV2_SPECIAL = set(r"_*[]()~`>#+-=|{}.!")


def escape_markdown_v2(text: str) -> str:
    """Escape *text* so it is safe inside a Telegram MarkdownV2 message.

    Args:
        text: Raw text that may contain MarkdownV2 reserved characters.

    Returns:
        The text with every reserved character backslash-escaped.
    """
    return "".join("\\" + ch if ch in _MDV2_SPECIAL else ch for ch in text)


def _retry_after_seconds(resp: httpx.Response) -> float:
    """Extract the retry delay from a 429 response (body, then header, then 1s)."""
    try:
        retry_after = resp.json().get("parameters", {}).get("retry_after")
        if retry_after is not None:
            return float(retry_after)
    except (ValueError, AttributeError, KeyError):
        pass
    header = resp.headers.get("Retry-After")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    return 1.0


async def send_message(text: str, *, parse_mode: str = "MarkdownV2") -> None:
    """Send a message to the configured Telegram chat.

    Never raises: on HTTP 429 it waits ``retry_after`` and retries once; on any
    other failure it logs and returns so the caller's run is unaffected.

    Args:
        text: Message body (already MarkdownV2-escaped when ``parse_mode`` is
            ``"MarkdownV2"``).
        parse_mode: Telegram parse mode. Defaults to ``"MarkdownV2"``.
    """
    try:
        settings = get_settings()
        url = f"{_API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for attempt in range(_MAX_RETRIES + 1):
                resp = await client.post(url, json=payload)
                if resp.status_code == 429 and attempt < _MAX_RETRIES:
                    delay = _retry_after_seconds(resp)
                    logger.warning("telegram_rate_limited", retry_after=delay)
                    await asyncio.sleep(delay)
                    continue
                resp.raise_for_status()
                return
    except Exception as exc:
        logger.error(
            "telegram_send_failed",
            error=f"{type(exc).__name__}: {str(exc)[:200]}",
        )
