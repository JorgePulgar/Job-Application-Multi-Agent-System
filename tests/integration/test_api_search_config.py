"""Integration tests for the search-config GET/PUT API."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from api.deps import get_profiles_dir
from api.main import app

_FULL_PROFILE: dict[str, Any] = {
    "username": "jorge",
    "nombre": "Jorge Pulgar",
    "email": "jorge@example.com",
    "location": "Madrid, España",
    "target_roles": ["ML Engineer"],
    "target_sectors": ["Fintech"],
    "experience_level": "junior",
    "tech_stack": ["Python"],
    "languages": ["Español"],
    "min_salary": 50000,
    "location_preference": {"modality": "hybrid", "cities": ["Madrid"]},
    "cv_summary": "Resumen del CV que NO debe cambiar.",
    "experiences": [{"company": "Acme", "role": "ML Engineer", "start_date": "2022-01"}],
}


@pytest.fixture()
def profiles_dir(tmp_path: Path) -> Path:
    (tmp_path / "jorge.yaml").write_text(yaml.safe_dump(_FULL_PROFILE), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def client(profiles_dir: Path) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_profiles_dir] = lambda: profiles_dir
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _read(profiles_dir: Path) -> dict[str, Any]:
    return yaml.safe_load((profiles_dir / "jorge.yaml").read_text(encoding="utf-8"))


def test_get_search_config_subset(client: TestClient) -> None:
    data = client.get("/users/jorge/search-config").json()
    assert data["target_roles"] == ["ML Engineer"]
    assert data["experience_level"] == "junior"
    assert data["location_preference"]["modality"] == "hybrid"
    assert "cv_summary" not in data  # subset only


def test_put_updates_and_preserves_cv(client: TestClient, profiles_dir: Path) -> None:
    body = {
        "target_roles": ["Data Engineer", "AI Engineer"],
        "target_sectors": ["SaaS"],
        "experience_level": "mid",
        "location_preference": {"modality": "remote", "cities": ["Barcelona"]},
        "min_salary": 60000,
    }
    resp = client.put("/users/jorge/search-config", json=body)
    assert resp.status_code == 200

    raw = _read(profiles_dir)
    assert raw["target_roles"] == ["Data Engineer", "AI Engineer"]
    assert raw["experience_level"] == "mid"
    assert raw["location_preference"]["modality"] == "remote"
    assert raw["min_salary"] == 60000
    # Untouched fields preserved.
    assert raw["cv_summary"] == "Resumen del CV que NO debe cambiar."
    assert raw["experiences"][0]["company"] == "Acme"
    assert raw["email"] == "jorge@example.com"


def test_put_invalid_experience_422_file_untouched(client: TestClient, profiles_dir: Path) -> None:
    before = _read(profiles_dir)
    body = {
        "target_roles": ["X"],
        "experience_level": "principiante",  # invalid enum
        "location_preference": {"modality": "remote", "cities": []},
    }
    resp = client.put("/users/jorge/search-config", json=body)
    assert resp.status_code == 422
    assert _read(profiles_dir) == before  # not written


def test_put_empty_roles_422(client: TestClient, profiles_dir: Path) -> None:
    before = _read(profiles_dir)
    body = {
        "target_roles": [],
        "location_preference": {"modality": "remote", "cities": []},
    }
    resp = client.put("/users/jorge/search-config", json=body)
    assert resp.status_code == 422
    assert _read(profiles_dir) == before


def test_put_negative_salary_422(client: TestClient) -> None:
    body = {
        "target_roles": ["X"],
        "location_preference": {"modality": "remote", "cities": []},
        "min_salary": -1,
    }
    assert client.put("/users/jorge/search-config", json=body).status_code == 422


def test_unknown_user_404(client: TestClient) -> None:
    assert client.get("/users/nobody/search-config").status_code == 404
    body = {"target_roles": ["X"], "location_preference": {"modality": "remote", "cities": []}}
    assert client.put("/users/nobody/search-config", json=body).status_code == 404
