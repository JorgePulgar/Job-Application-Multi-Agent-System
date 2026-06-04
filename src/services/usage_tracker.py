"""Token and cost tracking for Azure OpenAI calls within a single pipeline run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Azure OpenAI list prices per 1M tokens (USD), snapshot 2025-01-01.
# Source: https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/
# Cached-input tokens are billed at 50% of the standard input rate.
PRICING: dict[str, dict[str, float]] = {
    "mini": {
        "prompt": 0.15,
        "cached": 0.075,
        "completion": 0.60,
    },
    "4o": {
        "prompt": 2.50,
        "cached": 1.25,
        "completion": 10.00,
    },
}

# EUR/USD exchange rate snapshot 2025-01-01 (approximate).
_USD_TO_EUR: float = 0.92


@dataclass
class _DeploymentTotals:
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def cost_usd(self, deployment_key: str) -> float:
        """Return estimated USD cost for this deployment's recorded usage."""
        p = PRICING.get(deployment_key, PRICING["4o"])
        non_cached = max(0, self.prompt_tokens - self.cached_tokens)
        return (
            non_cached * p["prompt"]
            + self.cached_tokens * p["cached"]
            + self.completion_tokens * p["completion"]
        ) / 1_000_000


class UsageTracker:
    """Accumulates token counts across all LLM calls within one pipeline run.

    One instance is created per ``Orchestrator.run_for_user`` call and injected
    into the ``AzureOpenAIClient`` so every chat call contributes to the same
    budget snapshot.
    """

    def __init__(self) -> None:
        self._data: dict[str, _DeploymentTotals] = {}

    def record(
        self,
        deployment: str,
        prompt_tokens: int,
        cached_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Add token counts for one LLM call.

        Args:
            deployment: Deployment key (``"mini"`` or ``"4o"``).
            prompt_tokens: Total input tokens (includes cached subset).
            cached_tokens: Subset of prompt_tokens served from the cache.
            completion_tokens: Output tokens generated.
        """
        if deployment not in self._data:
            self._data[deployment] = _DeploymentTotals()
        t = self._data[deployment]
        t.prompt_tokens += prompt_tokens
        t.cached_tokens += cached_tokens
        t.completion_tokens += completion_tokens

    def summary(self) -> dict[str, Any]:
        """Return per-deployment token totals.

        Returns:
            Dict keyed by deployment name; values have prompt/cached/completion/total counts.
        """
        result: dict[str, Any] = {}
        for key, totals in self._data.items():
            result[key] = {
                "prompt_tokens": totals.prompt_tokens,
                "cached_tokens": totals.cached_tokens,
                "completion_tokens": totals.completion_tokens,
                "total_tokens": totals.total_tokens,
            }
        return result

    def total_cost_eur(self) -> float:
        """Return estimated total cost in EUR, rounded to 4 decimal places."""
        total_usd = sum(v.cost_usd(k) for k, v in self._data.items())
        return round(total_usd * _USD_TO_EUR, 4)
