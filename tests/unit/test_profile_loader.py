"""Unit tests for the profile loader service."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
from src.db.models import User
from src.models.user_profile import UserProfile
from src.services.profiles import load_profile, upsert_user_row

_EXAMPLES_DIR = (Path(__file__).parent.parent.parent / "config" / "users").resolve()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _copy_example(username: str, tmp_path: Path) -> Path:
    """Copy a *.yaml.example to a temp dir as *.yaml and return the path."""
    src = _EXAMPLES_DIR / f"{username}.yaml.example"
    dst = tmp_path / f"{username}.yaml"
    shutil.copy(src, dst)
    return dst


# ---------------------------------------------------------------------------
# load_profile — valid YAMLs
# ---------------------------------------------------------------------------


def test_load_jorge_example(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _copy_example("jorge", tmp_path)
    monkeypatch.chdir(tmp_path)
    # Point profiles dir to the tmp config structure
    (tmp_path / "config" / "users").mkdir(parents=True)
    shutil.copy(_EXAMPLES_DIR / "jorge.yaml.example", tmp_path / "config" / "users" / "jorge.yaml")

    profile = load_profile("jorge")
    assert profile.username == "jorge"
    assert len(profile.experiences) >= 1
    assert len(profile.education) >= 1
    assert profile.min_salary is not None and profile.min_salary > 0


def test_load_madalina_example(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config" / "users").mkdir(parents=True)
    shutil.copy(
        _EXAMPLES_DIR / "madalina.yaml.example",
        tmp_path / "config" / "users" / "madalina.yaml",
    )
    monkeypatch.chdir(tmp_path)

    profile = load_profile("madalina")
    assert profile.username == "madalina"
    assert len(profile.experiences) >= 1


# ---------------------------------------------------------------------------
# load_profile — error cases
# ---------------------------------------------------------------------------


def test_missing_file_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "config" / "users").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        load_profile("nonexistent")


def test_invalid_yaml_exits_with_field_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "config" / "users").mkdir(parents=True)
    bad_yaml = tmp_path / "config" / "users" / "bad.yaml"
    bad_yaml.write_text(
        "username: Bad_User\n"  # uppercase — invalid
        "nombre: Test\n"
        "email: not-an-email\n"
        "location: Madrid\n"
        "target_roles: []\n"
        "location_preference:\n"
        "  modality: hybrid\n"
        "cv_summary: resumen\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        load_profile("bad")


# ---------------------------------------------------------------------------
# upsert_user_row
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_session() -> Session:  # type: ignore[override]
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s  # type: ignore[misc]
    engine.dispose()


def _make_profile(**kwargs: object) -> UserProfile:
    base: dict[str, object] = {
        "username": "jorge",
        "nombre": "Jorge Pulgar",
        "email": "jorge@example.com",
        "location": "Madrid",
        "target_roles": ["ML Engineer"],
        "location_preference": {"modality": "hybrid", "cities": []},
        "cv_summary": "Resumen.",
    }
    base.update(kwargs)
    return UserProfile.model_validate(base)


def test_upsert_creates_new_row(mem_session: Session) -> None:
    profile = _make_profile()
    upsert_user_row(profile, session=mem_session)
    mem_session.flush()
    user = mem_session.query(User).filter_by(username="jorge").first()
    assert user is not None
    assert user.nombre == "Jorge Pulgar"


def test_upsert_updates_existing_row(mem_session: Session) -> None:
    profile = _make_profile()
    upsert_user_row(profile, session=mem_session)
    mem_session.flush()

    updated = _make_profile(nombre="Jorge P. Updated")
    upsert_user_row(updated, session=mem_session)
    mem_session.flush()

    users = mem_session.query(User).filter_by(username="jorge").all()
    assert len(users) == 1
    assert users[0].nombre == "Jorge P. Updated"
