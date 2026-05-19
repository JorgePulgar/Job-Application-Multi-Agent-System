"""Pydantic model for a scraped job offer, decoupled from the ORM layer."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.db.models import Offer


class Modalidad(StrEnum):
    """Work modality inferred from the offer."""

    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"
    unknown = "unknown"


def _normalize(text: str) -> str:
    """Normalize text for deduplication: lowercase, NFKD, strip punctuation, collapse spaces."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


class JobOffer(BaseModel):
    """A scraped job offer returned by any scraper agent.

    Attributes:
        titulo: Job title as listed in the offer.
        empresa: Company name as listed in the offer.
        ubicacion: Location string (city, region, or "remoto").
        modalidad: Inferred work modality.
        salario_min: Lower bound of the advertised salary range in EUR/year.
        salario_max: Upper bound of the advertised salary range in EUR/year.
        descripcion: Full job description text.
        url: Direct link to the offer.
        plataforma: Source platform identifier (e.g. ``"adzuna"``, ``"jooble"``).
        fecha_publicacion: Date the offer was published, if available.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    titulo: str = Field(..., description="Job title as listed in the offer.")
    empresa: str = Field(..., description="Company name as listed in the offer.")
    ubicacion: str = Field(default="", description="Location string.")
    modalidad: Modalidad = Field(default=Modalidad.unknown, description="Work modality.")
    salario_min: int | None = Field(default=None, description="Min salary EUR/year.")
    salario_max: int | None = Field(default=None, description="Max salary EUR/year.")
    descripcion: str = Field(default="", description="Full job description text.")
    url: str = Field(default="", description="Direct URL to the offer.")
    plataforma: str = Field(..., description="Source platform identifier.")
    fecha_publicacion: date | None = Field(
        default=None, description="Date the offer was published."
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def hash_unico(self) -> str:
        """SHA-256 hash of the normalized titulo + empresa + ubicacion.

        Used for exact deduplication across scraping runs.
        """
        combined = _normalize(self.titulo) + _normalize(self.empresa) + _normalize(self.ubicacion)
        return hashlib.sha256(combined.encode()).hexdigest()

    def to_db_offer(self, user_id: int, company_id: int | None = None) -> Offer:
        """Convert this model to a SQLAlchemy ``Offer`` ORM instance.

        Args:
            user_id: PK of the user row this offer belongs to.
            company_id: PK of an already-researched company row, if any.

        Returns:
            An unsaved ``Offer`` instance ready to be added to a session.
        """
        import datetime

        from src.db.models import Offer

        return Offer(
            user_id=user_id,
            company_id=company_id,
            titulo=self.titulo,
            empresa=self.empresa,
            ubicacion=self.ubicacion or None,
            descripcion=self.descripcion or None,
            url=self.url or None,
            fuente=self.plataforma,
            fecha_publicacion=datetime.datetime.combine(
                self.fecha_publicacion, datetime.time.min, tzinfo=datetime.UTC
            )
            if self.fecha_publicacion
            else None,
            fecha_detectada=datetime.datetime.now(datetime.UTC),
            hash_unico=self.hash_unico,
        )
