"""Unit tests for UsageTracker."""

from __future__ import annotations

from src.services.usage_tracker import PRICING, UsageTracker


def test_record_accumulates_tokens() -> None:
    tracker = UsageTracker()
    tracker.record("mini", prompt_tokens=100, cached_tokens=0, completion_tokens=50)
    tracker.record("mini", prompt_tokens=200, cached_tokens=50, completion_tokens=80)

    s = tracker.summary()
    assert s["mini"]["prompt_tokens"] == 300
    assert s["mini"]["cached_tokens"] == 50
    assert s["mini"]["completion_tokens"] == 130
    assert s["mini"]["total_tokens"] == 430


def test_record_multiple_deployments() -> None:
    tracker = UsageTracker()
    tracker.record("mini", 100, 0, 50)
    tracker.record("4o", 200, 100, 80)

    s = tracker.summary()
    assert "mini" in s
    assert "4o" in s
    assert s["4o"]["cached_tokens"] == 100


def test_cached_tokens_billed_at_reduced_rate() -> None:
    tracker = UsageTracker()
    # 1M cached tokens only — should cost at cached rate, not prompt rate
    tracker.record("4o", prompt_tokens=1_000_000, cached_tokens=1_000_000, completion_tokens=0)

    cost_eur = tracker.total_cost_eur()
    # 1M cached tokens at $1.25/M = $1.25, converted to EUR
    expected_usd = PRICING["4o"]["cached"] * 1.0  # 1M tokens
    from src.services.usage_tracker import _USD_TO_EUR

    expected_eur = round(expected_usd * _USD_TO_EUR, 4)
    assert cost_eur == expected_eur


def test_non_cached_prompt_tokens_billed_at_full_rate() -> None:
    tracker = UsageTracker()
    # 1M prompt tokens, none cached
    tracker.record("4o", prompt_tokens=1_000_000, cached_tokens=0, completion_tokens=0)

    cost_eur = tracker.total_cost_eur()
    expected_usd = PRICING["4o"]["prompt"] * 1.0
    from src.services.usage_tracker import _USD_TO_EUR

    expected_eur = round(expected_usd * _USD_TO_EUR, 4)
    assert cost_eur == expected_eur


def test_cost_rounds_to_4_decimals() -> None:
    tracker = UsageTracker()
    tracker.record("mini", 1, 0, 1)
    cost = tracker.total_cost_eur()
    assert cost == round(cost, 4)


def test_empty_tracker_returns_zero_cost() -> None:
    tracker = UsageTracker()
    assert tracker.total_cost_eur() == 0.0
    assert tracker.summary() == {}


def test_total_tokens_excludes_prompt_overlap() -> None:
    """total_tokens = prompt + completion, NOT prompt + cached + completion."""
    tracker = UsageTracker()
    tracker.record("mini", prompt_tokens=500, cached_tokens=300, completion_tokens=100)
    s = tracker.summary()
    assert s["mini"]["total_tokens"] == 600  # 500 + 100
