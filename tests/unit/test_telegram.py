"""Unit tests for the Telegram notifier service."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
import respx

from src.services import telegram
from src.services.telegram import escape_markdown_v2, send_message

_TOKEN = "TESTTOKEN"
_CHAT = "123456"
_URL = f"https://api.telegram.org/bot{_TOKEN}/sendMessage"


@pytest.fixture(autouse=True)
def _stub_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide Telegram credentials without requiring the full env."""
    monkeypatch.setattr(
        telegram,
        "get_settings",
        lambda: SimpleNamespace(telegram_bot_token=_TOKEN, telegram_chat_id=_CHAT),
    )


# ---------------------------------------------------------------------------
# escape_markdown_v2
# ---------------------------------------------------------------------------


def test_escape_markdown_v2_escapes_reserved_chars() -> None:
    assert escape_markdown_v2("a.b-c!") == "a\\.b\\-c\\!"
    assert escape_markdown_v2("(x) [y]") == "\\(x\\) \\[y\\]"


def test_escape_markdown_v2_leaves_plain_text() -> None:
    assert escape_markdown_v2("Resumen diario 2026") == "Resumen diario 2026"


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


@respx.mock
async def test_send_message_posts_expected_body() -> None:
    route = respx.post(_URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    await send_message("hola *mundo*")

    assert route.called
    sent = route.calls.last.request
    import json

    body = json.loads(sent.content)
    assert body == {
        "chat_id": _CHAT,
        "text": "hola *mundo*",
        "parse_mode": "MarkdownV2",
    }


@respx.mock
async def test_send_message_retries_on_429() -> None:
    route = respx.post(_URL).mock(
        side_effect=[
            httpx.Response(429, json={"parameters": {"retry_after": 0}}),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    await send_message("retry please")

    assert route.call_count == 2


@respx.mock
async def test_send_message_swallows_http_error() -> None:
    respx.post(_URL).mock(return_value=httpx.Response(500, json={"ok": False}))

    # Must not raise.
    await send_message("boom")


@respx.mock
async def test_send_message_swallows_transport_error() -> None:
    respx.post(_URL).mock(side_effect=httpx.ConnectError("no network"))

    # Must not raise.
    await send_message("offline")
