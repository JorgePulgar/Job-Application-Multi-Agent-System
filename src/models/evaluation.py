"""Pydantic model for the viability evaluator's structured output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from src.db.models import Evaluation as DbEvaluation

Recomendacion = Literal["aplicar", "dudar", "descartar"]


class ViabilityEvaluation(BaseModel):
    """Structured output of the ViabilityEvaluator agent.

    Attributes:
        score: Overall viability score from 0 (discard) to 100 (apply immediately).
        ventajas: Reasons in favour of applying (1-6 items).
        desventajas: Concerns or drawbacks (0-6 items).
        red_flags_match: User red-flag patterns that matched this offer.
        recomendacion: Final recommendation.
        reasoning: Free-text explanation supporting the score and recommendation.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    score: int = Field(..., ge=0, le=100, description="Viability score 0-100.")
    ventajas: list[str] = Field(..., min_length=1, max_length=6, description="Pros (1-6).")
    desventajas: list[str] = Field(default_factory=list, max_length=6, description="Cons (0-6).")
    red_flags_match: list[str] = Field(
        default_factory=list,
        description="User red-flag patterns that matched this offer.",
    )
    recomendacion: Recomendacion = Field(..., description="Final recommendation.")
    reasoning: str = Field(..., description="Explanation for the score and recommendation.")

    @field_validator("ventajas", "desventajas", "red_flags_match", mode="before")
    @classmethod
    def strip_list_items(cls, v: list[str]) -> list[str]:
        """Strip whitespace from each list element."""
        return [item.strip() for item in v if item.strip()]

    @model_validator(mode="after")
    def red_flags_block_aplicar(self) -> ViabilityEvaluation:
        """Reject 'aplicar' when red flags matched."""
        if self.red_flags_match and self.recomendacion == "aplicar":
            raise ValueError("recomendacion cannot be 'aplicar' when red_flags_match is non-empty")
        return self

    def to_db_row(self, offer_id: int) -> DbEvaluation:
        """Convert to an unsaved SQLAlchemy Evaluation ORM instance.

        Args:
            offer_id: FK to the evaluated offer.

        Returns:
            Unsaved ``db.Evaluation`` instance ready for ``session.add()``.
        """
        from src.db.models import Evaluation as DbEvaluation  # avoid circular at runtime

        return DbEvaluation(
            offer_id=offer_id,
            puntuacion=self.score,
            pros=self.ventajas,
            contras={"desventajas": self.desventajas, "red_flags_match": self.red_flags_match},
            recomendacion=self.recomendacion,
            razonamiento=self.reasoning,
        )
