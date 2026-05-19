"""Integration tests for `python -m src.cli filter` using a mocked LLM."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.cli as cli_module
from src.cli import cli
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Offer, User
from src.models.decisions import FilterDecision
from src.services.azure_openai import ChatResult, TokenUsage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine: Any) -> Generator[Session, None, None]:
    with Session(db_engine) as session:
        yield session


@pytest.fixture()
def seeded_db(db_engine: Any) -> None:
    """Insert a user and two 'nueva' offers into the in-memory DB."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()

        session.add(
            Offer(
                user_id=user.id,
                titulo="ML Engineer remoto",
                empresa="DataCo SL",
                fuente="adzuna",
                hash_unico="aaa111",
                estado=OfferEstado.nueva,
                descripcion="Rol de ML para startup fintech.",
            )
        )
        session.add(
            Offer(
                user_id=user.id,
                titulo="Soporte Técnico IT",
                empresa="SupportCo SL",
                fuente="jooble",
                hash_unico="bbb222",
                estado=OfferEstado.nueva,
                descripcion="Atención a usuarios de primer nivel.",
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

    def _make_result(relevant: bool, reason: str | None = None) -> ChatResult:
        return ChatResult(
            content="",
            parsed=FilterDecision(relevant=relevant, razon_descarte=reason),
            usage=TokenUsage(50, 0, 10, 60),
            latency_ms=20.0,
            model="gpt-4o-mini",
        )

    # First offer relevant, second (soporte) discarded (but will be short-circuited by red_flag)
    client.chat = AsyncMock(return_value=_make_result(True))
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
        target_roles=["ML Engineer"],
        red_flags=["soporte"],
        location_preference=LocationPreference(modality=Modality.hybrid),
        cv_summary="Resumen.",
    )
    monkeypatch.setattr(cli_module, "load_profile", lambda _: profile)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_filter_updates_db_states(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["filter", "--user", "jorge"])

    assert result.exit_code == 0, result.output

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars().all())

    estados = {o.titulo: o.estado for o in offers}
    # ML Engineer → filtrada (LLM returned relevant=True)
    assert estados["ML Engineer remoto"] == OfferEstado.filtrada
    # Soporte → descartada (red-flag short-circuit)
    assert estados["Soporte Técnico IT"] == OfferEstado.descartada


def test_filter_dry_run_does_not_change_db(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["filter", "--user", "jorge", "--dry-run"])

    assert result.exit_code == 0
    assert "dry-run" in result.output

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars().all())

    # All offers should still be 'nueva' after dry-run
    for offer in offers:
        assert offer.estado == OfferEstado.nueva, f"{offer.titulo} changed state in dry-run"


def test_filter_limit_flag_restricts_offers(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
    mock_llm_client: MagicMock,
) -> None:
    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        CliRunner().invoke(cli, ["filter", "--user", "jorge", "--limit", "1"])

    with Session(db_engine) as session:
        processed = list(
            session.execute(select(Offer).where(Offer.estado != OfferEstado.nueva)).scalars().all()
        )
    assert len(processed) == 1


def test_filter_shows_summary_in_output(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["filter", "--user", "jorge"])

    assert "Relevantes" in result.output
    assert "Descartadas" in result.output
    assert "Short-circuit" in result.output


def test_filter_unknown_user_exits_gracefully(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    result = CliRunner().invoke(cli, ["filter", "--user", "doesnotexist"])
    assert result.exit_code == 0
    assert "not found in DB" in result.output
