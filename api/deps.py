"""FastAPI dependency factories."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy.orm import Session

from src.db.base import _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and commit on exit."""
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_profiles_dir() -> Path:
    """Return the user YAML profiles directory."""
    import os

    return Path(os.getenv("PROFILES_DIR", "config/users"))
