"""Pydantic v2 models for user profiles loaded from YAML."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

_USERNAME_RE = re.compile(r"^[a-z0-9_]{2,32}$")


class Modality(StrEnum):
    """Work location preference."""

    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class Experience(BaseModel):
    """A single work experience entry."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: str
    role: str
    start_date: str
    end_date: str | None = None
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """An education entry."""

    model_config = ConfigDict(str_strip_whitespace=True)

    institution: str
    degree: str
    start_date: str
    end_date: str | None = None


class Certification(BaseModel):
    """A professional certification."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    issuer: str
    date: str


class LocationPreference(BaseModel):
    """Work location preference."""

    modality: Modality
    cities: list[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """Complete user profile used by every agent in the pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str
    nombre: str
    email: EmailStr
    phone: str | None = None
    location: str
    target_roles: list[str]
    target_sectors: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    min_salary: int | None = None
    location_preference: LocationPreference
    red_flags: list[str] = Field(default_factory=list)
    cv_summary: str
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Enforce lowercase alphanumeric/underscore, 2-32 chars."""
        if not _USERNAME_RE.match(v):
            raise ValueError(
                f"username '{v}' must be lowercase, alphanumeric/underscore, 2-32 characters"
            )
        return v

    @model_validator(mode="after")
    def validate_min_salary(self) -> UserProfile:
        """Ensure min_salary, when set, is a positive integer."""
        if self.min_salary is not None and self.min_salary <= 0:
            raise ValueError("min_salary must be a positive integer")
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> UserProfile:
        """Load and validate a UserProfile from a YAML file.

        Args:
            path: Filesystem path to the user YAML file.

        Returns:
            Validated ``UserProfile`` instance.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValidationError: If the YAML contents fail validation.
        """
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def cv_for_prompt(self) -> str:
        """Return the user CV formatted as Markdown for use in LLM prompts.

        The output is deterministic given the same profile data.
        """
        lines: list[str] = [
            f"# CV — {self.nombre}",
            "",
            f"**Email:** {self.email}",
            f"**Ubicación:** {self.location}",
            f"**Salario mínimo:** {self.min_salary:,} €/año" if self.min_salary else "",
            "",
            "## Resumen",
            self.cv_summary,
            "",
        ]

        if self.tech_stack:
            lines += ["## Stack tecnológico", ", ".join(self.tech_stack), ""]

        if self.languages:
            lines += ["## Idiomas", ", ".join(self.languages), ""]

        if self.experiences:
            lines.append("## Experiencia")
            for exp in self.experiences:
                end = exp.end_date or "actualidad"
                lines.append(f"\n### {exp.role} — {exp.company} ({exp.start_date} - {end})")
                for ach in exp.achievements:
                    lines.append(f"- {ach}")
                if exp.technologies:
                    lines.append(f"*Tecnologías:* {', '.join(exp.technologies)}")
            lines.append("")

        if self.education:
            lines.append("## Formación")
            for edu in self.education:
                end = edu.end_date or "actualidad"
                lines.append(f"- {edu.degree} — {edu.institution} ({edu.start_date} - {end})")
            lines.append("")

        if self.certifications:
            lines.append("## Certificaciones")
            for cert in self.certifications:
                lines.append(f"- {cert.name} ({cert.issuer}, {cert.date})")
            lines.append("")

        return "\n".join(line for line in lines if line is not None)
