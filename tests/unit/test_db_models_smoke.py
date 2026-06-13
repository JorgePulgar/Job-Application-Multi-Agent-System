"""Smoke tests for the DB ORM models using in-memory SQLite."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from src.db.base import Base
from src.db.enums import DraftEstado, OfferEstado, Recomendacion, RunEstado
from src.db.models import Draft, Evaluation, Offer, RunLog, User


@pytest.fixture(scope="module")
def session() -> Session:  # type: ignore[override]
    """In-memory SQLite session with schema applied via metadata (not Alembic)."""
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s  # type: ignore[misc]
    engine.dispose()


# ---------------------------------------------------------------------------
# Schema sanity
# ---------------------------------------------------------------------------


def test_all_tables_created(session: Session) -> None:
    inspector = inspect(session.bind)
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "companies",
        "offers",
        "evaluations",
        "drafts",
        "applications",
        "run_logs",
    } <= tables


def test_offers_indexes_exist(session: Session) -> None:
    inspector = inspect(session.bind)
    index_names = {idx["name"] for idx in inspector.get_indexes("offers")}
    assert "ix_offers_user_id" in index_names
    assert "ix_offers_estado" in index_names
    assert "ix_offers_fecha_detectada" in index_names


# ---------------------------------------------------------------------------
# Insert / read round-trip
# ---------------------------------------------------------------------------


def test_insert_user(session: Session) -> None:
    user = User(username="jorge", nombre="Jorge Pulgar")
    session.add(user)
    session.flush()
    assert user.id is not None
    fetched = session.get(User, user.id)
    assert fetched is not None
    assert fetched.username == "jorge"


def test_insert_offer(session: Session) -> None:
    user = session.execute(text("SELECT id FROM users WHERE username='jorge'")).fetchone()
    assert user is not None
    offer = Offer(
        user_id=user[0],
        titulo="ML Engineer",
        empresa="Acme SA",
        fuente="adzuna",
        hash_unico="abc123def456" + "0" * 52,
        estado=OfferEstado.nueva,
        fecha_detectada=datetime.datetime.now(datetime.UTC),
    )
    session.add(offer)
    session.flush()
    assert offer.id is not None
    fetched = session.get(Offer, offer.id)
    assert fetched is not None
    assert fetched.estado == OfferEstado.nueva


def test_insert_evaluation(session: Session) -> None:
    offer = session.execute(text("SELECT id FROM offers LIMIT 1")).fetchone()
    assert offer is not None
    ev = Evaluation(
        offer_id=offer[0],
        puntuacion=8,
        pros=["Buen salario"],
        contras=["Requiere viaje"],
        recomendacion=Recomendacion.solicitar,
        razonamiento="Encaja bien con el perfil.",
    )
    session.add(ev)
    session.flush()
    assert ev.id is not None
    fetched = session.get(Evaluation, ev.id)
    assert fetched is not None
    assert fetched.puntuacion == 8
    assert fetched.recomendacion == Recomendacion.solicitar


def test_insert_draft(session: Session) -> None:
    offer = session.execute(text("SELECT id, user_id FROM offers LIMIT 1")).fetchone()
    assert offer is not None
    draft = Draft(
        offer_id=offer[0],
        user_id=offer[1],
        asunto="Candidatura: ML Engineer en Acme SA",
        cuerpo_email="Estimado equipo,\n\nMe dirijo a ustedes...",
        carta_presentacion="Carta de presentación...",
        estado=DraftEstado.pendiente,
        intento_num=1,
    )
    session.add(draft)
    session.flush()
    assert draft.id is not None
    fetched = session.get(Draft, draft.id)
    assert fetched is not None
    assert fetched.estado == DraftEstado.pendiente


def test_insert_run_log(session: Session) -> None:
    user = session.execute(text("SELECT id FROM users WHERE username='jorge'")).fetchone()
    assert user is not None
    log = RunLog(
        user_id=user[0],
        fecha_inicio=datetime.datetime.now(datetime.UTC),
        ofertas_detectadas=5,
        ofertas_relevantes=2,
        borradores_generados=1,
        estado=RunEstado.completed,
    )
    session.add(log)
    session.flush()
    assert log.id is not None


def test_offers_composite_unique_exists(session: Session) -> None:
    inspector = inspect(session.bind)
    uniques = {uc["name"]: uc["column_names"] for uc in inspector.get_unique_constraints("offers")}
    assert "uq_offers_user_hash" in uniques
    assert uniques["uq_offers_user_hash"] == ["user_id", "hash_unico"]


def test_same_user_same_hash_rejected(session: Session) -> None:
    """A single user cannot hold the same offer hash twice (composite unique).

    Self-contained (creates its own user + first offer) so it does not depend on
    session state left by earlier tests.
    """
    user = User(username="dup_user", nombre="Dup")
    session.add(user)
    session.flush()
    duplicate_hash = "d" * 64
    session.add(
        Offer(
            user_id=user.id,
            titulo="ML Engineer",
            empresa="Acme SA",
            fuente="adzuna",
            hash_unico=duplicate_hash,
            estado=OfferEstado.nueva,
            fecha_detectada=datetime.datetime.now(datetime.UTC),
        )
    )
    session.flush()
    session.add(
        Offer(
            user_id=user.id,
            titulo="Otro titulo",
            empresa="Otra empresa",
            fuente="jooble",
            hash_unico=duplicate_hash,  # same user + same hash → must fail
            estado=OfferEstado.nueva,
            fecha_detectada=datetime.datetime.now(datetime.UTC),
        )
    )
    with pytest.raises(Exception):  # noqa: B017 — SQLAlchemy raises IntegrityError subclass
        session.flush()
    session.rollback()


def test_same_hash_allowed_across_users(session: Session) -> None:
    """Two different users CAN hold the same offer hash — per-user independence.

    Self-contained (creates its own users) so it does not depend on session
    state left by earlier tests.
    """
    user_a = User(username="user_a", nombre="A")
    user_b = User(username="user_b", nombre="B")
    session.add_all([user_a, user_b])
    session.flush()
    shared_hash = "f" * 64
    session.add_all(
        [
            Offer(
                user_id=user_a.id,
                titulo="ML Engineer",
                empresa="Acme SA",
                fuente="adzuna",
                hash_unico=shared_hash,
                estado=OfferEstado.nueva,
                fecha_detectada=datetime.datetime.now(datetime.UTC),
            ),
            Offer(
                user_id=user_b.id,
                titulo="ML Engineer",
                empresa="Acme SA",
                fuente="jooble",
                hash_unico=shared_hash,
                estado=OfferEstado.nueva,
                fecha_detectada=datetime.datetime.now(datetime.UTC),
            ),
        ]
    )
    session.flush()  # both rows with the same hash must coexist
    session.rollback()
