"""Migration test for the per-user offer unique constraint (e3f4a5b6c7d8).

Verifies the composite ``(user_id, hash_unico)`` migration applies over
pre-migration data, lets two users hold the same offer hash, still blocks a
single user from holding it twice, and round-trips up/down cleanly.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from src.db.enums import OfferEstado
from src.db.models import Offer, User

_PREV_REVISION = "d1e2f3a4b5c6"  # phase7_schema — the revision before this one
_HASH = "a" * 64
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _alembic_cfg(db_url: str) -> Config:
    """Build an Alembic config pointed at *db_url* and this repo's scripts."""
    cfg = Config()  # no ini file → env.py skips fileConfig
    cfg.set_main_option("script_location", str(_REPO_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _make_offer(user_id: int, hash_unico: str, fuente: str = "adzuna") -> Offer:
    return Offer(
        user_id=user_id,
        titulo="ML Engineer",
        empresa="Acme SA",
        fuente=fuente,
        hash_unico=hash_unico,
        estado=OfferEstado.nueva,
        fecha_detectada=_now(),
    )


def test_upgrade_allows_same_hash_across_users(tmp_path: Path) -> None:
    """Seed pre-migration data, upgrade, then two users share one offer hash."""
    db_url = f"sqlite:///{tmp_path / 'seeded.db'}"
    cfg = _alembic_cfg(db_url)

    # Bring the DB to the revision *before* this migration and seed data.
    command.upgrade(cfg, _PREV_REVISION)
    engine = create_engine(db_url)
    with Session(engine) as s:
        jorge = User(username="jorge", nombre="Jorge")
        madalina = User(username="madalina", nombre="Madalina")
        s.add_all([jorge, madalina])
        s.flush()
        jorge_id, madalina_id = jorge.id, madalina.id
        s.add(_make_offer(jorge_id, _HASH))  # one offer for jorge, global-unique era
        s.commit()
    engine.dispose()

    # Apply the composite-unique migration over the seeded data.
    command.upgrade(cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    uniques = {uc["name"]: uc["column_names"] for uc in inspector.get_unique_constraints("offers")}
    assert "uq_offers_user_hash" in uniques
    assert uniques["uq_offers_user_hash"] == ["user_id", "hash_unico"]
    assert "uq_offers_hash_unico" not in uniques

    with Session(engine) as s:
        # Same hash, different user → allowed now.
        s.add(_make_offer(madalina_id, _HASH, fuente="jooble"))
        s.commit()

    with Session(engine) as s:
        # Same hash, same user → still rejected by the composite constraint.
        s.add(_make_offer(madalina_id, _HASH))
        with pytest.raises(IntegrityError):
            s.flush()
        s.rollback()
    engine.dispose()


def test_migration_round_trips(tmp_path: Path) -> None:
    """Upgrade → downgrade → upgrade on an empty DB applies without error."""
    db_url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    cfg = _alembic_cfg(db_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, _PREV_REVISION)

    engine = create_engine(db_url)
    inspector = inspect(engine)
    uniques = {uc["name"] for uc in inspector.get_unique_constraints("offers")}
    assert "uq_offers_hash_unico" in uniques  # global unique restored
    assert "uq_offers_user_hash" not in uniques
    engine.dispose()

    command.upgrade(cfg, "head")  # re-apply cleanly
