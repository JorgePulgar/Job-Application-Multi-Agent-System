"""Profile router: read-only full YAML + editable search-config subset."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from api.deps import get_profiles_dir
from api.schemas import LocationPreferenceIO, SearchConfig
from src.models.user_profile import UserProfile

router = APIRouter(prefix="/users", tags=["profile"])

ProfilesDir = Annotated[Path, Depends(get_profiles_dir)]

# Keys this API is allowed to write back to the YAML. Everything else (CV,
# experiences, education, …) is preserved untouched.
_EDITABLE_KEYS = frozenset(
    {"target_roles", "target_sectors", "experience_level", "location_preference", "min_salary"}
)


def _profile_path(username: str, profiles_dir: Path) -> Path:
    path = profiles_dir / f"{username}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found for '{username}'")
    return path


def _load_raw(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


@router.get("/{username}/profile", response_model=dict[str, Any])
def get_profile(username: str, profiles_dir: ProfilesDir) -> dict[str, Any]:
    """Return the raw YAML profile as JSON (read-only)."""
    return _load_raw(_profile_path(username, profiles_dir))


@router.get("/{username}/search-config", response_model=SearchConfig)
def get_search_config(username: str, profiles_dir: ProfilesDir) -> SearchConfig:
    """Return just the editable search-config subset of the user's profile."""
    raw = _load_raw(_profile_path(username, profiles_dir))
    loc = raw.get("location_preference") or {}
    return SearchConfig(
        target_roles=raw.get("target_roles", []),
        target_sectors=raw.get("target_sectors", []),
        experience_level=raw.get("experience_level"),
        location_preference=LocationPreferenceIO(
            modality=loc.get("modality", "remote"),
            cities=loc.get("cities", []),
        ),
        min_salary=raw.get("min_salary"),
    )


@router.put("/{username}/search-config", response_model=SearchConfig)
def put_search_config(username: str, body: SearchConfig, profiles_dir: ProfilesDir) -> SearchConfig:
    """Update the editable search-config fields, preserving the rest of the YAML.

    Loads the existing YAML, patches only the editable keys, re-validates the
    whole profile, and writes it back atomically. On validation failure the file
    is left untouched and a 422 is returned.
    """
    path = _profile_path(username, profiles_dir)
    raw = _load_raw(path)

    patch = body.model_dump(mode="json")  # enums → str for YAML friendliness
    for key in _EDITABLE_KEYS:
        raw[key] = patch[key]

    try:
        UserProfile.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc

    _atomic_write_yaml(path, raw)
    return body


def _atomic_write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write *data* to *path* atomically (temp file in the same dir + replace)."""
    dump = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(dump)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise
