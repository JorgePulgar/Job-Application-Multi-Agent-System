"""Pydantic model for the application writer's structured output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from src.db.models import Draft as DbDraft

_MIN_BODY_LEN = 200


class Draft(BaseModel):
    """Structured output of the ApplicationWriter agent.

    Attributes:
        email_subject: Email subject line (≤120 chars).
        email_body: Email body in markdown.
        carta_presentacion: Optional cover letter in markdown.
        experiencias_destacadas: 3-5 bullets highlighting relevant experience.
        needs_manual_context: True when the draft could not be completed
            automatically and needs human context before use.
        flagged_reasons: Reasons the draft was flagged (e.g. prohibited words,
            missing specificity hook).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    email_subject: str = Field(default="", max_length=120, description="Email subject (≤120).")
    email_body: str = Field(default="", description="Email body (markdown).")
    carta_presentacion: str | None = Field(
        default=None, description="Optional cover letter (markdown)."
    )
    experiencias_destacadas: list[str] = Field(
        default_factory=list, min_length=3, max_length=5, description="3-5 highlight bullets."
    )
    needs_manual_context: bool = Field(default=False, description="Draft needs human context.")
    flagged_reasons: list[str] = Field(
        default_factory=list, description="Reasons the draft was flagged."
    )

    @field_validator("experiencias_destacadas", "flagged_reasons", mode="before")
    @classmethod
    def strip_list_items(cls, v: list[str]) -> list[str]:
        """Strip whitespace from each list element and drop empties."""
        return [item.strip() for item in v if item.strip()]

    @model_validator(mode="after")
    def require_content_when_not_flagged(self) -> Draft:
        """Enforce subject and body presence for non-flagged drafts.

        A complete draft (``needs_manual_context=False``) must have a non-empty
        subject and a body of at least ``_MIN_BODY_LEN`` characters. Flagged
        drafts are exempt because they are placeholders awaiting human context.
        """
        if self.needs_manual_context:
            return self
        if not self.email_subject:
            raise ValueError("email_subject required when needs_manual_context is False")
        if len(self.email_body) < _MIN_BODY_LEN:
            raise ValueError(
                f"email_body must be at least {_MIN_BODY_LEN} chars "
                "when needs_manual_context is False"
            )
        return self

    def to_db_row(self, offer_id: int, user_id: int) -> DbDraft:
        """Convert to an unsaved SQLAlchemy Draft ORM instance.

        Args:
            offer_id: FK to the offer this draft answers.
            user_id: FK to the user the draft is written for.

        Returns:
            Unsaved ``db.Draft`` instance ready for ``session.add()``.
        """
        from src.db.enums import DraftEstado
        from src.db.models import Draft as DbDraft  # avoid circular at runtime

        estado = (
            DraftEstado.needs_manual_context if self.needs_manual_context else DraftEstado.pendiente
        )
        return DbDraft(
            offer_id=offer_id,
            user_id=user_id,
            asunto=self.email_subject or None,
            cuerpo_email=self.email_body or None,
            carta_presentacion=self.carta_presentacion,
            estado=estado,
        )
