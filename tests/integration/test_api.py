"""Integration tests for the FastAPI dashboard API."""

from __future__ import annotations

import datetime
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.deps import get_db, get_profiles_dir
from api.main import app
from src.db.base import Base
from src.db.enums import DraftEstado, OfferEstado
from src.db.models import Application, Company, Draft, Evaluation, Offer, User

# ---------------------------------------------------------------------------
# Engine + DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine() -> Any:
    """Fresh in-memory SQLite per test; StaticPool shares one connection across threads."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def db_session(engine: Any) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def profiles_dir(tmp_path: Path) -> Path:
    """Write a minimal jorge.yaml into a temp dir."""
    profile: dict[str, Any] = {
        "username": "jorge",
        "nombre": "Jorge Test",
        "email": "jorge@example.com",
        "phone": "+34 600 000 000",
        "location": "Madrid",
        "target_roles": ["ML Engineer"],
        "target_sectors": ["Fintech"],
        "tech_stack": ["Python"],
        "red_flags": [],
        "min_salary": 40000,
        "location_preference": {"modality": "remote"},
        "cv_summary": "CV test.",
        "experiences": [],
        "education": [],
        "certifications": [],
        "languages": ["Spanish"],
    }
    (tmp_path / "jorge.yaml").write_text(yaml.dump(profile), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def seeded_db(db_session: Session) -> Session:
    """Seed user + company + offer + evaluation + draft; commit."""
    user = User(username="jorge", nombre="Jorge Test")
    db_session.add(user)
    db_session.flush()

    company = Company(nombre="Acme Corp", sector="SaaS")
    db_session.add(company)
    db_session.flush()

    offer = Offer(
        user_id=user.id,
        company_id=company.id,
        titulo="ML Engineer",
        empresa="Acme Corp",
        fuente="adzuna",
        hash_unico="abc123",
        estado=OfferEstado.borrador_generado,
        fecha_detectada=datetime.datetime.now(datetime.UTC),
    )
    db_session.add(offer)
    db_session.flush()

    db_session.add(
        Evaluation(
            offer_id=offer.id,
            puntuacion=80,
            pros=["Great stack"],
            contras={"desventajas": ["Long commute"], "red_flags_match": []},
            recomendacion="aplicar",
        )
    )
    db_session.flush()

    db_session.add(
        Draft(
            offer_id=offer.id,
            user_id=user.id,
            asunto="Candidatura ML Engineer",
            cuerpo_email="Hola, me interesa la posición.",
            estado=DraftEstado.pendiente,
        )
    )
    db_session.commit()
    return db_session


@pytest.fixture()
def client(
    engine: Any, seeded_db: Session, profiles_dir: Path
) -> Generator[TestClient, None, None]:
    """TestClient with per-request DB sessions from the shared StaticPool engine."""
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _override_profiles() -> Path:
        return profiles_dir

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_profiles_dir] = _override_profiles
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_draft(db: Session) -> Draft:
    d = db.query(Draft).filter(Draft.asunto == "Candidatura ML Engineer").first()
    assert d is not None
    return d


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------


def test_list_users(client: TestClient) -> None:
    resp = client.get("/users")
    assert resp.status_code == 200
    data = resp.json()
    assert any(u["username"] == "jorge" for u in data)


# ---------------------------------------------------------------------------
# GET /users/{username}/drafts
# ---------------------------------------------------------------------------


def test_list_drafts(client: TestClient) -> None:
    resp = client.get("/users/jorge/drafts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["offer_empresa"] == "Acme Corp"
    assert item["puntuacion"] == 80


def test_list_drafts_draft_ready_alias(client: TestClient) -> None:
    resp = client.get("/users/jorge/drafts?state=draft_ready")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_drafts_unknown_state_returns_empty(client: TestClient) -> None:
    resp = client.get("/users/jorge/drafts?state=aprobado")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_drafts_unknown_user(client: TestClient) -> None:
    assert client.get("/users/nobody/drafts").status_code == 404


def test_list_drafts_sort_score(client: TestClient) -> None:
    assert client.get("/users/jorge/drafts?sort=score").status_code == 200


def test_list_drafts_platform_filter(client: TestClient) -> None:
    assert client.get("/users/jorge/drafts?platform=adzuna").json()["total"] == 1
    assert client.get("/users/jorge/drafts?platform=jooble").json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /drafts/{id}
# ---------------------------------------------------------------------------


def test_get_draft_detail(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    resp = client.get(f"/drafts/{draft.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["asunto"] == "Candidatura ML Engineer"
    assert body["offer"]["empresa"] == "Acme Corp"
    assert body["evaluation"]["puntuacion"] == 80
    assert body["application"] is None


def test_get_draft_not_found(client: TestClient) -> None:
    assert client.get("/drafts/99999").status_code == 404


# ---------------------------------------------------------------------------
# PATCH /drafts/{id}
# ---------------------------------------------------------------------------


def test_patch_draft_updates_fields(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    resp = client.patch(
        f"/drafts/{draft.id}",
        json={"asunto": "Nuevo asunto", "cuerpo_email": "Cuerpo editado"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["asunto"] == "Nuevo asunto"
    assert body["cuerpo_email"] == "Cuerpo editado"
    # Unspecified field is left untouched.
    assert body["carta_presentacion"] == draft.carta_presentacion


def test_patch_draft_partial_leaves_others(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    resp = client.patch(f"/drafts/{draft.id}", json={"cuerpo_email": "Solo cuerpo"})
    assert resp.status_code == 200
    assert resp.json()["asunto"] == "Candidatura ML Engineer"


def test_patch_draft_not_found(client: TestClient) -> None:
    assert client.patch("/drafts/99999", json={"asunto": "x"}).status_code == 404


# ---------------------------------------------------------------------------
# POST /drafts/{id}/mark-sent
# ---------------------------------------------------------------------------


def test_mark_sent(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    resp = client.post(
        f"/drafts/{draft.id}/mark-sent",
        json={"method": "email", "notes": "Sent via Gmail"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["offer_estado"] == OfferEstado.enviada
    assert "application_id" in body


def test_mark_sent_with_ps_text(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    resp = client.post(
        f"/drafts/{draft.id}/mark-sent",
        json={"method": "portal", "ps_text": "Generado con IA"},
    )
    assert resp.status_code == 201


def test_mark_sent_idempotent_conflict(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    client.post(f"/drafts/{draft.id}/mark-sent", json={"method": "email"})
    resp2 = client.post(f"/drafts/{draft.id}/mark-sent", json={"method": "email"})
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# POST /drafts/{id}/discard
# ---------------------------------------------------------------------------


def test_discard_draft(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    resp = client.post(f"/drafts/{draft.id}/discard")
    assert resp.status_code == 200
    assert resp.json()["offer_estado"] == OfferEstado.descartada

    seeded_db.expire_all()
    draft_after = seeded_db.get(Draft, draft.id)
    assert draft_after is not None
    assert draft_after.estado == DraftEstado.rechazado


# ---------------------------------------------------------------------------
# POST /drafts/{id}/regenerate
# ---------------------------------------------------------------------------

_GOOD_BODY = (
    "Construí un pipeline con Kafka que procesa millones de eventos al día. "
    "En Acme Corp trabajáis con ese tipo de stack, así que el problema lo conozco bien. "
    "Trabajo a diario con Python y SQL. Puedo enviaros un recorrido de dos minutos por "
    "el repositorio, o lo vemos en una llamada corta cuando queráis."
)


def test_regenerate_draft(client: TestClient, seeded_db: Session) -> None:
    from src.models.draft import Draft as DraftModel

    draft = _get_draft(seeded_db)

    mock_result = DraftModel(
        email_subject="Nueva candidatura ML Engineer",
        email_body=_GOOD_BODY,
        experiencias_destacadas=["Pipeline Kafka", "Python", "MLOps"],
        needs_manual_context=False,
    )

    with patch("src.services.azure_openai.AzureOpenAIClient") as MockClient, patch(
        "src.agents.application_writer.ApplicationWriter.write",
        new_callable=AsyncMock,
    ) as mock_write:
        MockClient.return_value = MagicMock()
        mock_write.return_value = mock_result
        resp = client.post(f"/drafts/{draft.id}/regenerate")

    assert resp.status_code == 200
    body = resp.json()
    assert body["draft_id"] == draft.id
    assert body["needs_manual_context"] is False
    assert body["asunto"] == "Nueva candidatura ML Engineer"


# ---------------------------------------------------------------------------
# GET /users/{username}/history
# ---------------------------------------------------------------------------


def test_history_empty(client: TestClient) -> None:
    resp = client.get("/users/jorge/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_history_with_application(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    offer = seeded_db.query(Offer).filter(Offer.empresa == "Acme Corp").first()
    user = seeded_db.query(User).filter(User.username == "jorge").first()
    assert offer is not None and user is not None

    seeded_db.add(
        Application(
            draft_id=draft.id,
            offer_id=offer.id,
            user_id=user.id,
            metodo_envio="email",
            fecha_envio=datetime.datetime.now(datetime.UTC),
        )
    )
    seeded_db.commit()

    resp = client.get("/users/jorge/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["offer_empresa"] == "Acme Corp"
    assert body["items"][0]["metodo_envio"] == "email"


def test_history_state_filter(client: TestClient, seeded_db: Session) -> None:
    draft = _get_draft(seeded_db)
    offer = seeded_db.query(Offer).filter(Offer.empresa == "Acme Corp").first()
    user = seeded_db.query(User).filter(User.username == "jorge").first()
    assert offer is not None and user is not None

    seeded_db.add(
        Application(
            draft_id=draft.id,
            offer_id=offer.id,
            user_id=user.id,
            metodo_envio="email",
            fecha_envio=datetime.datetime.now(datetime.UTC),
            tipo_respuesta=None,
        )
    )
    seeded_db.commit()

    assert client.get("/users/jorge/history?state=applied").json()["total"] == 1
    assert client.get("/users/jorge/history?state=rejected").json()["total"] == 0


def test_history_unknown_user(client: TestClient) -> None:
    assert client.get("/users/nobody/history").status_code == 404


# ---------------------------------------------------------------------------
# GET /users/{username}/profile
# ---------------------------------------------------------------------------


def test_get_profile(client: TestClient) -> None:
    resp = client.get("/users/jorge/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "jorge"
    assert data["nombre"] == "Jorge Test"


def test_get_profile_not_found(client: TestClient) -> None:
    assert client.get("/users/nobody/profile").status_code == 404
