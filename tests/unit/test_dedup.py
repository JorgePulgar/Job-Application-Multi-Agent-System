"""Unit tests for the deduplication service."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
from src.db.models import Offer, User
from src.models.job_offer import JobOffer
from src.services.dedup import dedup_within_run, filter_existing

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _offer(titulo: str, empresa: str, ubicacion: str = "Madrid") -> JobOffer:
    return JobOffer(titulo=titulo, empresa=empresa, ubicacion=ubicacion, plataforma="test")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def user_id(db_session: Session) -> int:
    user = User(username="test_user", nombre="Test User")
    db_session.add(user)
    db_session.flush()
    return int(user.id)


def _insert_offer(session: Session, offer: JobOffer, user_id: int) -> None:
    row = Offer(
        user_id=user_id,
        titulo=offer.titulo,
        empresa=offer.empresa,
        ubicacion=offer.ubicacion,
        fuente=offer.plataforma,
        hash_unico=offer.hash_unico,
        estado="nueva",
    )
    session.add(row)
    session.flush()


# ---------------------------------------------------------------------------
# dedup_within_run — exact duplicates
# ---------------------------------------------------------------------------


def test_exact_dup_removed() -> None:
    o1 = _offer("ML Engineer", "Acme Corp")
    o2 = _offer("ML Engineer", "Acme Corp")  # same hash
    result = dedup_within_run([o1, o2])
    assert len(result) == 1
    assert result[0].titulo == "ML Engineer"


def test_exact_dup_different_companies_both_kept() -> None:
    o1 = _offer("ML Engineer", "Acme Corp", "Madrid")
    o2 = _offer("ML Engineer", "DataCorp", "Barcelona")  # different empresa → different hash + key
    result = dedup_within_run([o1, o2])
    assert len(result) == 2


def test_three_exact_same_keeps_one() -> None:
    offers = [_offer("Data Engineer", "Corp X")] * 3
    result = dedup_within_run(offers)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# dedup_within_run — near-duplicates
# ---------------------------------------------------------------------------


def test_near_dup_removed() -> None:
    # These differ only by accent and minor wording — WRatio should be >= 92
    o1 = _offer("Ingeniero Machine Learning", "Empresa ABC", "Barcelona")
    o2 = _offer("Ingeniero de Machine Learning", "Empresa ABC", "Barcelona")
    result = dedup_within_run([o1, o2])
    assert len(result) == 1


def test_near_dup_case_insensitive() -> None:
    o1 = _offer("DATA ENGINEER", "DataCorp", "Sevilla")
    o2 = _offer("data engineer", "DataCorp", "Sevilla")
    # hash_unico is already lowercased, so these have the same hash — exact dedup catches it
    result = dedup_within_run([o1, o2])
    assert len(result) == 1


def test_unrelated_offers_both_kept() -> None:
    o1 = _offer("Frontend Developer", "Startup XYZ", "Bilbao")
    o2 = _offer("Backend Engineer", "Company DEF", "Valencia")
    result = dedup_within_run([o1, o2])
    assert len(result) == 2


def test_empty_list_returns_empty() -> None:
    assert dedup_within_run([]) == []


def test_single_offer_returned_unchanged() -> None:
    o = _offer("AI Researcher", "University Lab")
    result = dedup_within_run([o])
    assert result == [o]


def test_threshold_boundary_strict() -> None:
    # Completely different offers must survive even at high threshold
    offers = [
        _offer("Contable Senior", "Gestoría Norte"),
        _offer("Ingeniero Mecánico", "Taller Sud"),
        _offer("Médico de Familia", "Clínica Este"),
    ]
    result = dedup_within_run(offers, threshold=92)
    assert len(result) == 3


def test_custom_threshold_zero_deduplicates_all_but_first() -> None:
    """Threshold 0 means every pair is a near-dup — only first survives."""
    offers = [
        _offer("ML Engineer", "Acme", "Madrid"),
        _offer("Data Scientist", "Corp B", "Barcelona"),
        _offer("AI Researcher", "Lab C", "Bilbao"),
    ]
    result = dedup_within_run(offers, threshold=0)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# filter_existing
# ---------------------------------------------------------------------------


def test_filter_existing_drops_known(db_session: Session, user_id: int) -> None:
    existing = _offer("ML Engineer", "Acme Corp")
    _insert_offer(db_session, existing, user_id)

    new = _offer("Data Engineer", "DataCorp")
    result = filter_existing([existing, new], db_session, user_id)
    assert len(result) == 1
    assert result[0].titulo == "Data Engineer"


def test_filter_existing_empty_offers(db_session: Session, user_id: int) -> None:
    result = filter_existing([], db_session, user_id)
    assert result == []


def test_filter_existing_no_overlap(db_session: Session, user_id: int) -> None:
    o1 = _offer("ML Engineer", "Acme Corp")
    o2 = _offer("Data Engineer", "DataCorp")
    result = filter_existing([o1, o2], db_session, user_id)
    assert len(result) == 2


def test_filter_existing_all_known(db_session: Session, user_id: int) -> None:
    o1 = _offer("ML Engineer", "Acme Corp")
    o2 = _offer("Data Engineer", "DataCorp")
    _insert_offer(db_session, o1, user_id)
    _insert_offer(db_session, o2, user_id)

    result = filter_existing([o1, o2], db_session, user_id)
    assert result == []


def test_filter_existing_scoped_to_user(db_session: Session) -> None:
    """An offer known for user A should NOT be filtered out for user B."""
    user_a = User(username="user_a", nombre="User A")
    user_b = User(username="user_b", nombre="User B")
    db_session.add_all([user_a, user_b])
    db_session.flush()

    offer = _offer("ML Engineer", "Acme Corp")
    _insert_offer(db_session, offer, int(user_a.id))

    result = filter_existing([offer], db_session, int(user_b.id))
    assert len(result) == 1
