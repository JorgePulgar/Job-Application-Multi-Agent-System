"""User profile loading and DB upsert service."""

from __future__ import annotations

import sys
from pathlib import Path

import structlog
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.db.base import get_session
from src.db.models import User
from src.models.user_profile import UserProfile

log = structlog.get_logger(__name__)

_PROFILES_DIR = Path("config") / "users"


def load_profile(username: str) -> UserProfile:
    """Load and validate a user profile from ``config/users/<username>.yaml``.

    Args:
        username: The username whose YAML file to load.

    Returns:
        Validated ``UserProfile`` instance.

    Raises:
        SystemExit: On missing file or validation error (prints a human-readable
            message instead of a stack trace).
    """
    path = _PROFILES_DIR / f"{username}.yaml"
    if not path.exists():
        print(
            f"Error: profile not found at '{path}'.\n"
            f"Copy '{path}.example' to '{path}' and fill in your details.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        profile = UserProfile.from_yaml(path)
    except ValidationError as exc:
        lines = ["Error: invalid profile YAML — fix the following fields:\n"]
        for err in exc.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            lines.append(f"  • {field}: {err['msg']}")
        print("\n".join(lines), file=sys.stderr)
        sys.exit(1)

    log.info("profile loaded", username=username)
    return profile


def upsert_user_row(profile: UserProfile, session: Session | None = None) -> None:
    """Insert or update the ``users`` table row for *profile*.

    Args:
        profile: Validated user profile to persist.
        session: Optional existing session. When omitted a new session is opened
            and committed automatically.
    """

    def _do_upsert(s: Session) -> None:
        existing = s.query(User).filter_by(username=profile.username).first()
        if existing is None:
            s.add(User(username=profile.username, nombre=profile.nombre))
            log.info("user row created", username=profile.username)
        else:
            existing.nombre = profile.nombre
            log.info("user row updated", username=profile.username)

    if session is not None:
        _do_upsert(session)
    else:
        with get_session() as s:
            _do_upsert(s)
