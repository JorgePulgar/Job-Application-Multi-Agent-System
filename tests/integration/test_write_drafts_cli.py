"""Integration tests for `python -m src.cli write-drafts` with a real in-memory DB."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.cli as cli_module
from src.cli import cli
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Company, Evaluation, Offer, User
from src.db.models import Draft as DbDraft
from src.models.draft import Draft
from src.services import draft_persistence
from src.services.azure_openai import ChatResult, TokenUsage

_GOOD_BODY = (
    "Construí un pipeline con Kafka que procesa millones de eventos al día. En Alpha "
    "trabajáis con ese tipo de stack, así que el problema lo conozco bien. Trabajo a "
    "diario con Python y SQL. Puedo enviaros un recorrido de dos minutos por el "
    "repositorio, o lo vemos en una llamada corta cuando queráis."
)
_BAD_BODY = (
    "Construí un pipeline con Kafka que procesa millones de eventos al día. En vuestra "
    "empresa trabajáis con ese tipo de stack, así que el problema lo conozco bien. "
    "Trabajo a diario con Python y SQL. Puedo enviaros un recorrido de dos minutos por "
    "el repositorio, o lo vemos en una llamada corta cuando queráis."
)


def _draft(*, good: bool = True) -> Draft:
    return Draft(
        email_subject="ingeniero de datos para Alpha",
        email_body=_GOOD_BODY if good else _BAD_BODY,
        experiencias_destacadas=["Kafka pipeline", "Python", "SQL"],
    )


def _chat_result(draft: Draft) -> ChatResult:
    return ChatResult(
        content="",
        parsed=draft,
        usage=TokenUsage(
            prompt_tokens=900, cached_tokens=600, completion_tokens=300, total_tokens=1200
        ),
        latency_ms=1000.0,
        model="gpt-4o",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def seeded_db(db_engine: Any) -> None:
    """1 user, 1 company (Alpha), 3 evaluada offers: aplicar, dudar, descartar."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()

        co = Company(nombre="Alpha SL", sector="fintech", descripcion="Fintech.")
        session.add(co)
        session.flush()

        specs = [
            ("ML Engineer", "a001", "aplicar", 85),
            ("Data Scientist", "a002", "dudar", 60),
            ("Sales Rep", "a003", "descartar", 20),
        ]
        for titulo, h, rec, score in specs:
            offer = Offer(
                user_id=user.id,
                company_id=co.id,
                titulo=titulo,
                empresa="Alpha SL",
                fuente="adzuna",
                hash_unico=h,
                estado=OfferEstado.evaluada,
                descripcion="Rol en Alpha.",
            )
            session.add(offer)
            session.flush()
            session.add(
                Evaluation(
                    offer_id=offer.id,
                    puntuacion=score,
                    pros=["Stack alineado"],
                    contras={"desventajas": [], "red_flags_match": []},
                    recomendacion=rec,
                    razonamiento="Motivo.",
                )
            )
        session.commit()


@pytest.fixture()
def patch_get_session(db_engine: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _fake() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session
            session.commit()

    monkeypatch.setattr(cli_module, "get_session", _fake)


@pytest.fixture()
def mock_llm_client() -> MagicMock:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_chat_result(_draft(good=True)))
    return client


@pytest.fixture()
def patch_azure_client(mock_llm_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "AzureOpenAIClient", lambda: mock_llm_client)


@pytest.fixture()
def mock_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.models.user_profile import LocationPreference, Modality, UserProfile

    profile = UserProfile(
        username="jorge",
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["ML Engineer", "Data Scientist"],
        tech_stack=["Python"],
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="Resumen de prueba.",
    )
    monkeypatch.setattr(cli_module, "load_profile", lambda _: profile)


@pytest.fixture(autouse=True)
def _tmp_drafts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_persistence, "_DRAFTS_ROOT", tmp_path / "drafts")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_writes_drafts_for_aplicar_and_dudar(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
    db_engine: Any,
) -> None:
    """aplicar + dudar processed (descartar excluded); both pass lint → 2 drafts."""
    result = CliRunner().invoke(cli, ["write-drafts", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert mock_llm_client.chat.await_count == 2  # descartar excluded

    with Session(db_engine) as session:
        rows = list(session.execute(select(DbDraft)).scalars().all())
        offers = {o.titulo: o.estado for o in session.execute(select(Offer)).scalars().all()}
    assert len(rows) == 2
    assert offers["ML Engineer"] == OfferEstado.borrador_generado
    assert offers["Data Scientist"] == OfferEstado.borrador_generado
    assert offers["Sales Rep"] == OfferEstado.evaluada  # untouched


def test_summary_reports_counts_and_tokens(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    result = CliRunner().invoke(cli, ["write-drafts", "--user", "jorge"])
    assert "Borradores escritos:  2" in result.output
    assert "Necesitan contexto:" in result.output
    assert "Tokens usados:" in result.output


def test_one_passes_one_flagged_after_retries(
    seeded_db: None,
    patch_get_session: None,
    mock_profile: None,
    monkeypatch: pytest.MonkeyPatch,
    db_engine: Any,
) -> None:
    """First offer passes lint (1 call); second fails 3x and is flagged."""
    client = MagicMock()
    client.chat = AsyncMock(
        side_effect=[
            _chat_result(_draft(good=True)),  # offer 1, passes
            _chat_result(_draft(good=False)),  # offer 2, attempt 0
            _chat_result(_draft(good=False)),  # offer 2, retry 1
            _chat_result(_draft(good=False)),  # offer 2, retry 2
        ]
    )
    monkeypatch.setattr(cli_module, "AzureOpenAIClient", lambda: client)

    result = CliRunner().invoke(cli, ["write-drafts", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert client.chat.await_count == 4
    assert "Borradores escritos:  1" in result.output
    assert "Necesitan contexto:   1" in result.output

    with Session(db_engine) as session:
        rows = {r.offer_id: r.estado for r in session.execute(select(DbDraft)).scalars().all()}
        offers = {o.titulo: o.estado for o in session.execute(select(Offer)).scalars().all()}
    # Offers are ordered fecha_detectada.desc(): Data Scientist (inserted later) is
    # processed first (good draft → borrador_generado); ML Engineer second (flagged).
    assert offers["Data Scientist"] == OfferEstado.borrador_generado
    assert offers["ML Engineer"] == OfferEstado.evaluada
    assert "needs_manual_context" in set(rows.values())


def test_recomendacion_filter(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
) -> None:
    """--recomendacion aplicar processes only the aplicar offer."""
    result = CliRunner().invoke(
        cli, ["write-drafts", "--user", "jorge", "--recomendacion", "aplicar"]
    )
    assert result.exit_code == 0, result.output
    assert mock_llm_client.chat.await_count == 1


def test_limit_flag(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
) -> None:
    result = CliRunner().invoke(cli, ["write-drafts", "--user", "jorge", "--limit", "1"])
    assert result.exit_code == 0, result.output
    assert mock_llm_client.chat.await_count == 1


def test_dry_run_does_not_persist(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
    tmp_path: Path,
) -> None:
    result = CliRunner().invoke(cli, ["write-drafts", "--dry-run", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output

    with Session(db_engine) as session:
        rows = list(session.execute(select(DbDraft)).scalars().all())
        offers = list(session.execute(select(Offer)).scalars().all())
    assert rows == []
    for offer in offers:
        assert offer.estado == OfferEstado.evaluada
    assert not (tmp_path / "drafts").exists()


def test_unknown_user_exits_gracefully(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    result = CliRunner().invoke(cli, ["write-drafts", "--user", "ghost"])
    assert result.exit_code == 0
    assert "not found in DB" in result.output


def test_no_offers_exits_gracefully(
    db_engine: Any,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    with Session(db_engine) as session:
        session.add(User(username="jorge", nombre="Jorge"))
        session.commit()

    result = CliRunner().invoke(cli, ["write-drafts", "--user", "jorge"])
    assert result.exit_code == 0
    assert "No hay" in result.output
