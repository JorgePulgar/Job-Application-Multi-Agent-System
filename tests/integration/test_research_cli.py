"""Integration tests for `python -m src.cli research-companies` using a mocked LLM."""

from __future__ import annotations

import datetime
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog.testing
from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import src.cli as cli_module
from src.cli import cli
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Company, Offer, User
from src.models.company import CompanyDossier, TamanoEmpresa
from src.services.azure_openai import ChatResult, TokenUsage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_research_output() -> MagicMock:
    from src.agents.company_researcher import _ResearchOutput

    return _ResearchOutput(
        sector="fintech",
        tamano=TamanoEmpresa.startup,
        ubicacion_hq="Madrid, España",
        descripcion="Plataforma de pagos B2B.",
        stack_tecnologico=["python", "kubernetes"],
        cultura_notas=["Trabajo remoto."],
        red_flags_detectadas=[],
        productos_o_servicios=["API de pagos"],
        equipo_ai_detectado=True,
    )


def _make_chat_result() -> ChatResult:
    return ChatResult(
        content="",
        parsed=_make_research_output(),
        usage=TokenUsage(
            prompt_tokens=500, cached_tokens=200, completion_tokens=150, total_tokens=650
        ),
        latency_ms=800.0,
        model="gpt-4o",
    )


def _make_cached_dossier() -> dict[str, Any]:
    dossier = CompanyDossier(
        sector="saas",
        tamano=TamanoEmpresa.pyme,
        ubicacion_hq="Barcelona, España",
        descripcion="Empresa SaaS de RRHH.",
        stack_tecnologico=["java"],
        cultura_notas=[],
        red_flags_detectadas=[],
        productos_o_servicios=["HR Suite"],
        equipo_ai_detectado=False,
        fuentes=[],
    )
    return dossier.model_dump(mode="json")


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
    """Insert a user with 3 filtrada offers (3 companies, one already cached)."""
    with Session(db_engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()

        # Pre-cached company — should not trigger LLM.
        # Use naive datetimes: SQLite strips timezone info on round-trip.
        now_naive = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        cached_company = Company(
            nombre="CachedCo SL",
            sector="saas",
            descripcion="Empresa SaaS.",
            dossier_json=_make_cached_dossier(),
            fecha_research=now_naive - datetime.timedelta(days=5),
            expira_en=now_naive + datetime.timedelta(days=25),
        )
        session.add(cached_company)
        session.flush()

        # Offer linked to the cached company (company_id still None → needs linking)
        session.add(
            Offer(
                user_id=user.id,
                titulo="HR Analyst",
                empresa="CachedCo SL",
                fuente="adzuna",
                hash_unico="cached001",
                estado=OfferEstado.filtrada,
                descripcion="Oferta para CachedCo.",
            )
        )
        # Two fresh companies — should each trigger one LLM call
        session.add(
            Offer(
                user_id=user.id,
                titulo="ML Engineer",
                empresa="FreshCo SL",
                fuente="adzuna",
                hash_unico="fresh001",
                estado=OfferEstado.filtrada,
                descripcion="Rol de ML para startup fintech.",
            )
        )
        session.add(
            Offer(
                user_id=user.id,
                titulo="Backend Engineer",
                empresa="NewCo SL",
                fuente="jooble",
                hash_unico="new001",
                estado=OfferEstado.filtrada,
                descripcion="Rol de backend.",
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
    client.chat = AsyncMock(return_value=_make_chat_result())
    return client


@pytest.fixture()
def patch_azure_client(mock_llm_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "AzureOpenAIClient", lambda: mock_llm_client)


@pytest.fixture(autouse=True)
def patch_settings() -> Generator[None, None, None]:
    """Patch get_settings in the agent so tests don't need real env vars."""
    fake = MagicMock()
    fake.company_research_ttl_days = 30
    with patch("src.agents.company_researcher.get_settings", return_value=fake):
        yield


@pytest.fixture()
def mock_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.models.user_profile import LocationPreference, Modality, UserProfile

    profile = UserProfile(
        username="jorge",
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["ML Engineer"],
        red_flags=[],
        location_preference=LocationPreference(modality=Modality.hybrid),
        cv_summary="Resumen.",
    )
    monkeypatch.setattr(cli_module, "load_profile", lambda _: profile)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_research_fires_llm_only_for_uncached_companies(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
) -> None:
    """3 companies seeded, 1 cached → only 2 LLM calls expected."""
    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["research-companies", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert mock_llm_client.chat.await_count == 2


def test_research_links_offers_to_companies(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    """After the run, all filtrada offers should have company_id set and estado=investigada."""
    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["research-companies", "--user", "jorge"])

    assert result.exit_code == 0, result.output

    with Session(db_engine) as session:
        offers = list(session.execute(select(Offer)).scalars().all())

    for offer in offers:
        assert offer.company_id is not None, f"offer '{offer.titulo}' has no company_id"
        assert offer.estado == OfferEstado.investigada, f"offer '{offer.titulo}' not investigada"


def test_research_dry_run_does_not_write_new_companies(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    db_engine: Any,
) -> None:
    """dry-run skips all LLM calls and writes nothing."""
    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["--dry-run", "research-companies", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output

    with Session(db_engine) as session:
        company_count = len(list(session.execute(select(Company)).scalars().all()))

    # Only the pre-seeded CachedCo should exist — no new rows
    assert company_count == 1


def test_research_limit_flag_restricts_companies(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
    mock_llm_client: MagicMock,
) -> None:
    """--limit 1 processes at most 1 offer (may be the cached company → 0 LLM calls)."""
    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["research-companies", "--user", "jorge", "--limit", "1"])

    assert result.exit_code == 0, result.output
    # At most 1 LLM call (could be 0 if the single offer is the cached company)
    assert mock_llm_client.chat.await_count <= 1


def test_research_shows_summary_in_output(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        result = CliRunner().invoke(cli, ["research-companies", "--user", "jorge"])

    assert result.exit_code == 0, result.output
    assert "Resumen" in result.output
    assert "Cache hits" in result.output
    assert "Errores" in result.output


def test_research_unknown_user_exits_gracefully(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    result = CliRunner().invoke(cli, ["research-companies", "--user", "doesnotexist"])
    assert result.exit_code == 0
    assert "not found in DB" in result.output


def test_research_logs_contain_no_pii(
    seeded_db: None,
    patch_get_session: None,
    patch_azure_client: None,
    mock_profile: None,
) -> None:
    """Structured log events must not contain email addresses or phone numbers."""
    import re

    email_re = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
    # Matches E.164 (+34666777888) or grouped formats (666 777 888 / 666-777-888).
    # Deliberately excludes ISO datetime strings (YYYY-MM-DDT...) which look like digit runs.
    phone_re = re.compile(r"\+\d{1,3}[\s\-]?\d{6,}|\b\d{3}[\s\-]\d{3}[\s\-]\d{3,4}\b")

    with (
        structlog.testing.capture_logs() as logs,
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        CliRunner().invoke(cli, ["research-companies", "--user", "jorge"])

    for event in logs:
        for key, value in event.items():
            text = str(value)
            assert not email_re.search(text), f"PII (email) found in log field '{key}': {text!r}"
            assert not phone_re.search(text), f"PII (phone) found in log field '{key}': {text!r}"
