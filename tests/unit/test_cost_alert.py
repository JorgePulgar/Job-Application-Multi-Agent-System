"""Unit tests for the per-run cost alert."""

from __future__ import annotations

import datetime

import pytest

from src import orchestrator as orch
from src.orchestrator import Orchestrator, RunResult, format_cost_alert


def _result(username: str, cost: float) -> RunResult:
    now = datetime.datetime.now(datetime.UTC)
    return RunResult(
        username=username,
        fecha_inicio=now,
        fecha_fin=now,
        ofertas_scrapeadas=10,
        ofertas_filtradas=4,
        drafts_generados=2,
        coste_estimado_eur=cost,
    )


# ---------------------------------------------------------------------------
# format_cost_alert
# ---------------------------------------------------------------------------


def test_alert_none_below_threshold() -> None:
    results = [_result("jorge", 0.20), _result("madalina", 0.30)]
    assert format_cost_alert(results, threshold=1.00) is None


def test_alert_fires_on_global_total() -> None:
    # No single user exceeds 1.00 but the global total (1.20) does.
    results = [_result("jorge", 0.70), _result("madalina", 0.50)]
    alert = format_cost_alert(results, threshold=1.00)
    assert alert is not None
    assert "ALERTA DE COSTE" in alert
    assert "1\\.2000 EUR" in alert  # global cost, MarkdownV2-escaped


def test_alert_fires_on_single_user() -> None:
    results = [_result("jorge", 1.50), _result("madalina", 0.10)]
    alert = format_cost_alert(results, threshold=1.00)
    assert alert is not None
    assert "jorge" in alert
    assert "madalina" not in alert  # only offenders listed in the breakdown


# ---------------------------------------------------------------------------
# run_for_all_users wiring
# ---------------------------------------------------------------------------


async def test_run_sends_exactly_one_alert_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[str] = []

    async def _fake_send(text: str, *, parse_mode: str = "MarkdownV2") -> None:
        sent.append(text)

    monkeypatch.setattr(orch.telegram, "send_message", _fake_send)
    monkeypatch.setattr(orch, "_cost_alert_threshold", lambda: 1.00)

    o = Orchestrator()
    monkeypatch.setattr(o, "_discover_usernames", lambda: ["jorge"])

    async def _fake_run(username: str) -> RunResult:
        return _result(username, 2.00)

    monkeypatch.setattr(o, "run_for_user", _fake_run)

    await o.run_for_all_users()

    # One summary + exactly one alert.
    assert len(sent) == 2
    assert "ALERTA DE COSTE" in sent[1]


async def test_run_sends_no_alert_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[str] = []

    async def _fake_send(text: str, *, parse_mode: str = "MarkdownV2") -> None:
        sent.append(text)

    monkeypatch.setattr(orch.telegram, "send_message", _fake_send)
    monkeypatch.setattr(orch, "_cost_alert_threshold", lambda: 1.00)

    o = Orchestrator()
    monkeypatch.setattr(o, "_discover_usernames", lambda: ["jorge"])

    async def _fake_run(username: str) -> RunResult:
        return _result(username, 0.10)

    monkeypatch.setattr(o, "run_for_user", _fake_run)

    await o.run_for_all_users()

    # Only the summary; no alert.
    assert len(sent) == 1
    assert "ALERTA DE COSTE" not in sent[0]
