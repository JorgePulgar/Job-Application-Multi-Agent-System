"""SQLAlchemy declarative base and session factory."""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DB_PATH = Path("data") / "state.db"
_DB_URL = f"sqlite+pysqlite:///{_DB_PATH}"

engine = create_engine(
    _DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

_SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


@contextlib.contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager that yields a SQLAlchemy session and commits on exit.

    Yields:
        An open ``Session`` bound to the application SQLite database.
    """
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
