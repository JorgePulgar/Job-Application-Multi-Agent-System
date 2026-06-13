"""Unit tests for UserProfile Pydantic models."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.models.user_profile import (
    ExperienceLevel,
    LocationPreference,
    Modality,
    UserProfile,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_VALID: dict[str, object] = {
    "username": "jorge",
    "nombre": "Jorge Pulgar",
    "email": "jorge@example.com",
    "location": "Madrid, España",
    "target_roles": ["ML Engineer", "Data Engineer"],
    "location_preference": {"modality": "hybrid", "cities": ["Madrid"]},
    "cv_summary": "Ingeniero con experiencia en ML y datos.",
}

FULL_VALID: dict[str, object] = {
    **MINIMAL_VALID,
    "phone": "+34 612 345 678",
    "target_sectors": ["Fintech", "Salud"],
    "tech_stack": ["Python", "PyTorch", "SQL"],
    "languages": ["Español (nativo)", "Inglés (C1)"],
    "min_salary": 50000,
    "red_flags": ["empresa sin datos"],
    "experiences": [
        {
            "company": "Acme Corp",
            "role": "Data Scientist",
            "start_date": "2021-01",
            "end_date": "2024-06",
            "achievements": ["Reduje latencia un 30 %"],
            "technologies": ["Python", "Spark"],
        }
    ],
    "education": [
        {
            "institution": "UPM",
            "degree": "Ingeniería Informática",
            "start_date": "2015",
            "end_date": "2020",
        }
    ],
    "certifications": [{"name": "AWS ML Specialty", "issuer": "Amazon", "date": "2023-05"}],
}


# ---------------------------------------------------------------------------
# Construction / round-trip
# ---------------------------------------------------------------------------


def test_minimal_profile_valid() -> None:
    profile = UserProfile.model_validate(MINIMAL_VALID)
    assert profile.username == "jorge"
    assert profile.min_salary is None
    assert profile.experiences == []


# ---------------------------------------------------------------------------
# experience_level
# ---------------------------------------------------------------------------


def test_experience_level_defaults_none() -> None:
    """Profiles without experience_level stay valid (backward-compatible)."""
    profile = UserProfile.model_validate(MINIMAL_VALID)
    assert profile.experience_level is None


def test_experience_level_parsed() -> None:
    profile = UserProfile.model_validate({**MINIMAL_VALID, "experience_level": "junior"})
    assert profile.experience_level is ExperienceLevel.junior


def test_experience_level_invalid_rejected() -> None:
    with pytest.raises(ValidationError):
        UserProfile.model_validate({**MINIMAL_VALID, "experience_level": "principiante"})


def test_experience_level_year_range() -> None:
    assert ExperienceLevel.junior.year_range == (0, 2)
    assert ExperienceLevel.mid.year_range == (2, 5)
    assert ExperienceLevel.senior.year_range == (5, None)


def test_experience_level_keywords() -> None:
    assert "junior" in ExperienceLevel.junior.keywords("es")
    assert "becario" in ExperienceLevel.junior.keywords("es")
    assert "entry level" in ExperienceLevel.junior.keywords("en")
    # Unknown language falls back to English.
    assert ExperienceLevel.senior.keywords("fr") == ExperienceLevel.senior.keywords("en")


def test_full_profile_valid() -> None:
    profile = UserProfile.model_validate(FULL_VALID)
    assert profile.min_salary == 50000
    assert len(profile.experiences) == 1
    assert profile.experiences[0].company == "Acme Corp"
    assert len(profile.education) == 1
    assert len(profile.certifications) == 1


def test_from_yaml_round_trip(tmp_path: Path) -> None:
    yaml_file = tmp_path / "jorge.yaml"
    yaml_file.write_text(yaml.dump(FULL_VALID), encoding="utf-8")
    profile = UserProfile.from_yaml(yaml_file)
    assert profile.username == "jorge"
    assert profile.email == "jorge@example.com"
    assert profile.location_preference.modality == Modality.hybrid


def test_from_yaml_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        UserProfile.from_yaml(tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# Username validator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_username",
    [
        "J",  # too short
        "a" * 33,  # too long
        "Jorge",  # uppercase
        "jo-rge",  # hyphen not allowed
        "jo rge",  # space not allowed
        "1",  # single char
    ],
)
def test_invalid_username(bad_username: str) -> None:
    data = {**MINIMAL_VALID, "username": bad_username}
    with pytest.raises(ValidationError, match="username"):
        UserProfile.model_validate(data)


@pytest.mark.parametrize("good_username", ["ab", "jorge_1", "a" * 32, "user123"])
def test_valid_username(good_username: str) -> None:
    profile = UserProfile.model_validate({**MINIMAL_VALID, "username": good_username})
    assert profile.username == good_username


# ---------------------------------------------------------------------------
# Email validator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_email", ["not-an-email", "missing@", "@nodomain", ""])
def test_invalid_email(bad_email: str) -> None:
    data = {**MINIMAL_VALID, "email": bad_email}
    with pytest.raises(ValidationError):
        UserProfile.model_validate(data)


# ---------------------------------------------------------------------------
# min_salary validator
# ---------------------------------------------------------------------------


def test_negative_min_salary_rejected() -> None:
    data = {**MINIMAL_VALID, "min_salary": -1000}
    with pytest.raises(ValidationError, match="min_salary"):
        UserProfile.model_validate(data)


def test_zero_min_salary_rejected() -> None:
    data = {**MINIMAL_VALID, "min_salary": 0}
    with pytest.raises(ValidationError, match="min_salary"):
        UserProfile.model_validate(data)


def test_positive_min_salary_accepted() -> None:
    profile = UserProfile.model_validate({**MINIMAL_VALID, "min_salary": 1})
    assert profile.min_salary == 1


# ---------------------------------------------------------------------------
# cv_for_prompt
# ---------------------------------------------------------------------------


def test_cv_for_prompt_contains_key_sections() -> None:
    profile = UserProfile.model_validate(FULL_VALID)
    cv = profile.cv_for_prompt()
    assert "Jorge Pulgar" in cv
    assert "Stack tecnológico" in cv
    assert "Experiencia" in cv
    assert "Acme Corp" in cv
    assert "Formación" in cv
    assert "Certificaciones" in cv
    assert "AWS ML Specialty" in cv


def test_cv_for_prompt_is_deterministic() -> None:
    profile = UserProfile.model_validate(FULL_VALID)
    assert profile.cv_for_prompt() == profile.cv_for_prompt()


def test_cv_for_prompt_minimal_no_optional_sections() -> None:
    profile = UserProfile.model_validate(MINIMAL_VALID)
    cv = profile.cv_for_prompt()
    assert "Experiencia" not in cv
    assert "Formación" not in cv
    assert "Certificaciones" not in cv


# ---------------------------------------------------------------------------
# signature_html
# ---------------------------------------------------------------------------


def test_signature_html_contains_name_and_email() -> None:
    profile = UserProfile.model_validate(MINIMAL_VALID)
    sig = profile.signature_html()
    assert "Jorge Pulgar" in sig
    assert "mailto:jorge@example.com" in sig
    assert sig.startswith("<div")


def test_signature_html_includes_links_when_present() -> None:
    data = {
        **MINIMAL_VALID,
        "github_url": "https://github.com/JorgePulgar",
        "linkedin_url": "https://www.linkedin.com/in/jorgepulgar/",
    }
    sig = UserProfile.model_validate(data).signature_html()
    assert "https://github.com/JorgePulgar" in sig
    assert "GitHub" in sig
    assert "LinkedIn" in sig


def test_signature_html_omits_absent_links() -> None:
    sig = UserProfile.model_validate(MINIMAL_VALID).signature_html()
    assert "GitHub" not in sig
    assert "LinkedIn" not in sig


def test_signature_html_has_no_dashes() -> None:
    data = {
        **MINIMAL_VALID,
        "github_url": "https://github.com/JorgePulgar",
        "linkedin_url": "https://www.linkedin.com/in/jorgepulgar/",
    }
    sig = UserProfile.model_validate(data).signature_html()
    assert "—" not in sig
    assert "–" not in sig  # noqa: RUF001


# ---------------------------------------------------------------------------
# LocationPreference
# ---------------------------------------------------------------------------


def test_location_preference_modality_enum() -> None:
    lp = LocationPreference(modality=Modality.remote, cities=[])
    assert lp.modality == Modality.remote


def test_invalid_modality() -> None:
    with pytest.raises(ValidationError):
        LocationPreference.model_validate({"modality": "flying", "cities": []})
