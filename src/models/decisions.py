"""Pydantic models for agent decision outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class FilterDecision(BaseModel):
    """Decision produced by the OfferFilter agent for a single offer.

    This model is used as the structured-output schema when querying the LLM,
    so field names and types must match what the model is asked to return.
    """

    relevant: bool
    razon_descarte: str | None = Field(
        default=None,
        max_length=200,
        description="Motivo del descarte (máximo 200 caracteres). Solo si relevant=false.",
    )


@dataclass
class FilterBatchSummary:
    """Aggregated statistics from running OfferFilter over a list of offers."""

    decisions: list[FilterDecision] = field(default_factory=list)
    relevant_count: int = 0
    discarded_count: int = 0
    red_flag_count: int = 0
    total_prompt_tokens: int = 0
    total_cached_tokens: int = 0
    total_completion_tokens: int = 0
