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


# Inclusive years-of-experience range per level; upper bound ``None`` = open-ended.
_EXPERIENCE_YEARS: dict[str, tuple[int, int | None]] = {
    "junior": (0, 2),
    "mid": (2, 5),
    "senior": (5, None),
}

# Per-language search keywords used to bias scraper queries toward a seniority.
_EXPERIENCE_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "junior": {
        "es": ["junior", "trainee", "becario", "prácticas", "sin experiencia"],
        "en": ["junior", "entry level", "graduate", "trainee", "intern"],
    },
    "mid": {
        "es": ["semi-senior", "ssr", "mid", "intermedio"],
        "en": ["mid", "mid-level", "intermediate"],
    },
    "senior": {
        "es": ["senior", "sénior", "lead", "principal"],
        "en": ["senior", "lead", "staff", "principal"],
    },
}


class ExperienceLevel(StrEnum):
    """Seniority a user is searching for, driving experience-based filtering.

    The single source of truth for the level → years-of-experience mapping and
    the per-language search keywords; both the scrapers (Task 05) and any future
    locale-aware prompt reuse these instead of redefining them.
    """

    junior = "junior"
    mid = "mid"
    senior = "senior"

    @property
    def year_range(self) -> tuple[int, int | None]:
        """Return the inclusive ``(min_years, max_years)`` for this level.

        ``max_years`` is ``None`` for ``senior`` (open-ended).
        """
        return _EXPERIENCE_YEARS[self.value]

    def keywords(self, lang: str) -> list[str]:
        """Return search keywords for this level in *lang* (``"es"``/``"en"``).

        Falls back to English keywords for any unrecognised language.
        """
        by_lang = _EXPERIENCE_KEYWORDS[self.value]
        return by_lang.get(lang, by_lang["en"])


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
    github_url: str | None = None
    linkedin_url: str | None = None
    location: str
    target_roles: list[str]
    target_sectors: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    min_salary: int | None = None
    experience_level: ExperienceLevel | None = None
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

    def signature_html(self) -> str:
        """Return the user's email signature as an inline-styled HTML block.

        Built deterministically from profile data so it is identical across
        drafts and never invented by the model. GitHub and LinkedIn links are
        included only when present on the profile.

        Returns:
            A single ``<div>`` HTML string with name, email, and any links.
        """
        link_style = 'style="color: #333; text-decoration: none;"'
        sep = "\n  &nbsp;&middot;&nbsp;\n  "

        links: list[str] = [f'<a href="mailto:{self.email}" {link_style}>{self.email}</a>']
        if self.github_url:
            links.append(f'<a href="{self.github_url}" {link_style}>GitHub</a>')
        if self.linkedin_url:
            links.append(f'<a href="{self.linkedin_url}" {link_style}>LinkedIn</a>')

        return (
            '<div style="font-family: Arial, Helvetica, sans-serif; '
            'font-size: 14px; color: #333;">\n'
            f"  {self.nombre}<br>\n  "
            f"{sep.join(links)}\n"
            "</div>"
        )
