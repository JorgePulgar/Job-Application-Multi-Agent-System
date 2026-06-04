"""Profile router: read-only user YAML as JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_profiles_dir

router = APIRouter(prefix="/users", tags=["profile"])

ProfilesDir = Annotated[Path, Depends(get_profiles_dir)]


@router.get("/{username}/profile", response_model=dict[str, Any])
def get_profile(username: str, profiles_dir: ProfilesDir) -> dict[str, Any]:
    """Return the raw YAML profile as JSON (read-only)."""
    path = profiles_dir / f"{username}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found for '{username}'")

    with path.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data
