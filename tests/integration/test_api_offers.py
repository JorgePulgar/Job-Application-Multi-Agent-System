"""Integration tests for the per-user offers listing API."""

from __future__ import annotations

import datetime
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.deps import get_db
from api.main import app
from src.db.base import Base
from src.db.enums import DraftEstado, OfferEstado, Recomendacion
from src.db.models import Draft, Evaluation, Offer, User


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


@pytest.fixture()
def engine() -> Any:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def seeded(engine: Any) -> None:
    """Seed two users; jorge gets offers across estados, madalina gets one."""
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as s:
        jorge = User(username="jorge", nombre="Jorge")
        madalina = User(username="madalina", nombre="Madalina")
        s.add_all([jorge, madalina])
        s.flush()

        def _offer(user_id: int, h: str, estado: OfferEstado, fuente: str = "adzuna") -> Offer:
            return Offer(
                user_id=user_id,
                titulo="ML Engineer",
                empresa="Acme Corp",
                ubicacion="Madrid",
                fuente=fuente,
                url="https://example.com/o",
                hash_unico=h,
                estado=estado,
                fecha_detectada=_now(),
            )

        # jorge: 2 nueva, 1 filtrada, 1 evaluada(+evaluation), 1 borrador_generado(+draft)
        j_nueva1 = _offer(jorge.id, "j1" + "0" * 62, OfferEstado.nueva)
        j_nueva2 = _offer(jorge.id, "j2" + "0" * 62, OfferEstado.nueva, fuente="jooble")
        j_filtrada = _offer(jorge.id, "j3" + "0" * 62, OfferEstado.filtrada)
        j_eval = _offer(jorge.id, "j4" + "0" * 62, OfferEstado.evaluada)
        j_draft = _offer(jorge.id, "j5" + "0" * 62, OfferEstado.borrador_generado)
        # madalina: same hash as one of jorge's, proving per-user independence
        m_nueva = _offer(madalina.id, "j1" + "0" * 62, OfferEstado.nueva)
        s.add_all([j_nueva1, j_nueva2, j_filtrada, j_eval, j_draft, m_nueva])
        s.flush()

        s.add(
            Evaluation(
                offer_id=j_eval.id,
                puntuacion=80,
                pros=["x"],
                contras={"desventajas": [], "red_flags_match": []},
                recomendacion=Recomendacion.solicitar,
            )
        )
        s.add(
            Draft(
                offer_id=j_draft.id,
                user_id=jorge.id,
                asunto="Candidatura",
                estado=DraftEstado.pendiente,
            )
        )
        s.commit()


@pytest.fixture()
def client(engine: Any, seeded: None) -> Generator[TestClient, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_lists_all_states_for_user(client: TestClient) -> None:
    resp = client.get("/users/jorge/offers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5  # jorge has 5 offers across estados
    assert {item["estado"] for item in data["items"]} == {
        "nueva",
        "filtrada",
        "evaluada",
        "borrador_generado",
    }


def test_per_user_scoping(client: TestClient) -> None:
    """madalina sees only her offer, not jorge's — even with a shared hash."""
    resp = client.get("/users/madalina/offers")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_estado_filter(client: TestClient) -> None:
    resp = client.get("/users/jorge/offers", params={"estado": "nueva"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(i["estado"] == "nueva" for i in data["items"])


def test_plataforma_and_flags(client: TestClient) -> None:
    resp = client.get("/users/jorge/offers", params={"estado": "borrador_generado"})
    item = resp.json()["items"][0]
    assert item["has_draft"] is True
    assert item["draft_id"] is not None  # deep-link target present
    resp_eval = client.get("/users/jorge/offers", params={"estado": "evaluada"})
    eval_item = resp_eval.json()["items"][0]
    assert eval_item["has_evaluation"] is True
    assert eval_item["draft_id"] is None  # evaluated but no draft


def test_invalid_estado_422(client: TestClient) -> None:
    resp = client.get("/users/jorge/offers", params={"estado": "bogus"})
    assert resp.status_code == 422


def test_unknown_user_404(client: TestClient) -> None:
    assert client.get("/users/nobody/offers").status_code == 404


def test_counts_endpoint(client: TestClient) -> None:
    resp = client.get("/users/jorge/offers/counts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["nueva"] == 2
    assert data["counts"]["filtrada"] == 1
    assert data["total"] == 5
    # Only j_eval has an evaluation row → 1 analizada, 4 sin_analizar.
    assert data["buckets"] == {"analizadas": 1, "sin_analizar": 4}


def test_bucket_filter(client: TestClient) -> None:
    sin = client.get("/users/jorge/offers", params={"bucket": "sin_analizar"})
    assert sin.status_code == 200
    assert sin.json()["total"] == 4
    assert all(i["has_evaluation"] is False for i in sin.json()["items"])

    ana = client.get("/users/jorge/offers", params={"bucket": "analizadas"})
    assert ana.json()["total"] == 1
    assert ana.json()["items"][0]["has_evaluation"] is True


def test_invalid_bucket_422(client: TestClient) -> None:
    assert client.get("/users/jorge/offers", params={"bucket": "bogus"}).status_code == 422
