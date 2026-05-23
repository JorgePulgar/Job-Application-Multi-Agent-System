"""Pydantic model for the structured company research dossier."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class TamanoEmpresa(StrEnum):
    """Approximate company size category."""

    startup = "startup"
    pyme = "pyme"
    grande = "grande"
    enterprise = "enterprise"
    unknown = "unknown"


def _dedup(values: list[str]) -> list[str]:
    """Remove duplicate strings, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        s = v.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _dedup_lower(values: list[str]) -> list[str]:
    """Deduplicate and lowercase strings, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        s = v.strip().lower()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


class CompanyDossier(BaseModel):
    """Structured output produced by CompanyResearcher, stored in ``companies.dossier_json``.

    Attributes:
        sector: Industry sector (e.g. "fintech", "salud", "e-commerce").
        tamano: Approximate company size category.
        ubicacion_hq: City and country of headquarters.
        descripcion: Short narrative description of the company and its mission.
        stack_tecnologico: Deduplicated, lowercased list of technologies used.
        cultura_notas: Free-text notes about company culture, values, or work environment.
        red_flags_detectadas: Potential concerns found during research (e.g. layoffs, bad reviews).
        productos_o_servicios: Main products or services offered.
        equipo_ai_detectado: Whether an AI/ML team or function was explicitly found.
        fuentes: Source URLs used during research.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    sector: str = Field(..., description="Industry sector.")
    tamano: TamanoEmpresa = Field(
        default=TamanoEmpresa.unknown, description="Approximate company size."
    )
    ubicacion_hq: str = Field(..., description="City and country of headquarters.")
    descripcion: str = Field(..., description="Short narrative description of the company.")
    stack_tecnologico: list[str] = Field(
        default_factory=list, description="Technologies used (deduplicated, lowercased)."
    )
    cultura_notas: list[str] = Field(
        default_factory=list, description="Notes on company culture and values."
    )
    red_flags_detectadas: list[str] = Field(
        default_factory=list, description="Potential concerns found during research."
    )
    productos_o_servicios: list[str] = Field(
        default_factory=list, description="Main products or services."
    )
    equipo_ai_detectado: bool = Field(default=False, description="Whether an AI/ML team was found.")
    fuentes: list[HttpUrl] = Field(
        default_factory=list, description="Source URLs used during research."
    )

    @field_validator("stack_tecnologico", mode="before")
    @classmethod
    def dedup_and_lowercase_stack(cls, v: list[str]) -> list[str]:
        """Lowercase and deduplicate the tech stack list."""
        return _dedup_lower(v)

    @field_validator(
        "cultura_notas", "red_flags_detectadas", "productos_o_servicios", mode="before"
    )
    @classmethod
    def dedup_text_list(cls, v: list[str]) -> list[str]:
        """Deduplicate text lists preserving original casing."""
        return _dedup(v)

    def to_summary_for_prompt(self) -> str:
        """Return a concise markdown summary (≤ ~300 tokens) for inclusion in downstream prompts.

        Returns:
            Markdown-formatted string with the most relevant dossier fields.
        """
        descripcion_short = self.descripcion[:400] + ("…" if len(self.descripcion) > 400 else "")
        stack = ", ".join(self.stack_tecnologico) or "—"
        productos = ", ".join(self.productos_o_servicios) or "—"
        cultura = "; ".join(self.cultura_notas) or "—"
        red_flags = "; ".join(self.red_flags_detectadas) or "Ninguna"
        ai_label = "Sí" if self.equipo_ai_detectado else "No"

        header = (
            f"**Sector:** {self.sector} | **Tamaño:** {self.tamano} | **HQ:** {self.ubicacion_hq}"
        )
        return (
            f"{header}\n\n"
            f"**Descripción:** {descripcion_short}\n\n"
            f"**Stack tecnológico:** {stack}\n\n"
            f"**Productos/Servicios:** {productos}\n\n"
            f"**Cultura:** {cultura}\n\n"
            f"**Equipo AI detectado:** {ai_label}\n\n"
            f"**Red flags:** {red_flags}"
        )
