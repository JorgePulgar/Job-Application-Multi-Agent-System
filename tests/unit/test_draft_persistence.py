"""Unit tests for src/services/draft_persistence.py."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Draft as DbDraft
from src.db.models import Evaluation, Offer, User
from src.models.draft import Draft
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.services import draft_persistence

_BODY = (
    "Construí un pipeline con Kafka que procesa millones de eventos al día. En Acme "
    "trabajáis con ese stack, así que el problema lo conozco. Puedo enviaros un "
    "recorrido de 2 minutos por el repositorio o lo vemos en una llamada corta."
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture(autouse=True)
def _tmp_drafts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_persistence, "_DRAFTS_ROOT", tmp_path / "drafts")


def _profile() -> UserProfile:
    return UserProfile(
        username="jorge",
        nombre="Jorge Pulgar",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["Data Engineer"],
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="Ingeniero de datos.",
    )


def _make_offer(session: Session, *, with_eval: bool = True, empresa: str = "Acme Corp") -> Offer:
    user = User(username="jorge", nombre="Jorge Pulgar")
    session.add(user)
    session.flush()
    offer = Offer(
        user_id=user.id,
        titulo="Data Engineer",
        empresa=empresa,
        url="https://jobs.example.com/123",
        fuente="adzuna",
        hash_unico="abc123",
        estado=OfferEstado.evaluada,
    )
    session.add(offer)
    session.flush()
    if with_eval:
        session.add(
            Evaluation(
                offer_id=offer.id,
                puntuacion=82,
                pros=["Stack alineado"],
                contras={},
                recomendacion="aplicar",
                razonamiento="Buen encaje.",
            )
        )
        session.flush()
        session.refresh(offer)
    return offer


def _draft(**overrides: object) -> Draft:
    data: dict[str, object] = {
        "email_subject": "ingeniero de datos para Acme",
        "email_body": _BODY,
        "carta_presentacion": None,
        "experiencias_destacadas": ["Kafka pipeline", "Python", "SQL"],
        "needs_manual_context": False,
        "flagged_reasons": [],
    }
    data.update(overrides)
    return Draft.model_validate(data)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_folds_and_sanitizes() -> None:
    assert draft_persistence.slugify("Açme & Co!! / Señor") == "acme_co_senor"


def test_slugify_never_empty() -> None:
    assert draft_persistence.slugify("!!!") == "draft"


# ---------------------------------------------------------------------------
# DB insert + file write
# ---------------------------------------------------------------------------


def test_save_creates_db_row_and_file(session: Session) -> None:
    offer = _make_offer(session)
    path = draft_persistence.save_draft(_draft(), offer, _profile(), session)

    assert path.exists()
    rows = session.scalars(select(DbDraft).where(DbDraft.offer_id == offer.id)).all()
    assert len(rows) == 1
    assert rows[0].asunto == "ingeniero de datos para Acme"
    assert rows[0].estado == "pendiente"


def test_save_sets_offer_estado_borrador_generado(session: Session) -> None:
    offer = _make_offer(session)
    draft_persistence.save_draft(_draft(), offer, _profile(), session)
    assert offer.estado == OfferEstado.borrador_generado


def test_save_filename_format(session: Session) -> None:
    offer = _make_offer(session)
    path = draft_persistence.save_draft(_draft(), offer, _profile(), session)
    # {YYYY-MM-DD}_{slug}.md, slug from empresa_titulo
    assert path.name.endswith("_acme_corp_data_engineer.md")
    assert path.parent.name == "jorge"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_save_twice_updates_not_duplicates(session: Session) -> None:
    offer = _make_offer(session)
    draft_persistence.save_draft(_draft(), offer, _profile(), session)
    draft_persistence.save_draft(
        _draft(email_subject="asunto actualizado para Acme"), offer, _profile(), session
    )

    rows = session.scalars(select(DbDraft).where(DbDraft.offer_id == offer.id)).all()
    assert len(rows) == 1
    assert rows[0].asunto == "asunto actualizado para Acme"
    assert rows[0].intento_num == 2


# ---------------------------------------------------------------------------
# Frontmatter / content
# ---------------------------------------------------------------------------


def test_file_frontmatter_and_sections(session: Session) -> None:
    offer = _make_offer(session)
    path = draft_persistence.save_draft(_draft(), offer, _profile(), session)
    text = path.read_text(encoding="utf-8")

    assert "offer_url: https://jobs.example.com/123" in text
    assert "empresa: Acme Corp" in text
    assert "score: 82" in text
    assert "recomendacion: aplicar" in text
    assert "needs_manual_context: false" in text
    assert "## Asunto" in text
    assert "## Cuerpo del email" in text
    assert "## Experiencias destacadas" in text


def test_frontmatter_handles_missing_evaluation(session: Session) -> None:
    offer = _make_offer(session, with_eval=False)
    path = draft_persistence.save_draft(_draft(), offer, _profile(), session)
    text = path.read_text(encoding="utf-8")
    assert "score: N/A" in text
    assert "recomendacion: N/A" in text


# ---------------------------------------------------------------------------
# Flagged drafts
# ---------------------------------------------------------------------------


def test_flagged_draft_written_with_reasons(session: Session) -> None:
    offer = _make_offer(session)
    flagged = Draft(
        email_subject="",
        email_body="",
        needs_manual_context=True,
        flagged_reasons=["sin dato específico de la empresa"],
        experiencias_destacadas=["a", "b", "c"],
    )
    path = draft_persistence.save_draft(flagged, offer, _profile(), session)
    text = path.read_text(encoding="utf-8")

    assert "NECESITA CONTEXTO MANUAL" in text
    assert "sin dato específico de la empresa" in text
    assert "needs_manual_context: true" in text


def test_flagged_draft_offer_estado_unchanged(session: Session) -> None:
    offer = _make_offer(session)
    flagged = Draft(
        email_subject="",
        email_body="",
        needs_manual_context=True,
        flagged_reasons=["motivo"],
        experiencias_destacadas=["a", "b", "c"],
    )
    draft_persistence.save_draft(flagged, offer, _profile(), session)
    assert offer.estado == OfferEstado.evaluada

    row = session.scalars(select(DbDraft).where(DbDraft.offer_id == offer.id)).one()
    assert row.estado == "needs_manual_context"
