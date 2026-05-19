"""Unit tests for src/agents/offer_filter.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.offer_filter import OfferFilter, OfferFilterError
from src.db.enums import OfferEstado
from src.models.decisions import FilterDecision
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.services.azure_openai import ChatResult, TokenUsage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_offer(
    *,
    id: int = 1,
    titulo: str = "ML Engineer",
    empresa: str = "Acme SL",
    ubicacion: str = "Madrid",
    descripcion: str = "Buscamos ML Engineer con experiencia en Python.",
    estado: str = OfferEstado.nueva,
    user_id: int = 1,
    fuente: str = "adzuna",
) -> MagicMock:
    offer = MagicMock()
    offer.id = id
    offer.titulo = titulo
    offer.empresa = empresa
    offer.ubicacion = ubicacion
    offer.descripcion = descripcion
    offer.estado = estado
    offer.user_id = user_id
    offer.fuente = fuente
    offer.razon_descarte = None
    return offer


def _make_profile(
    *,
    target_roles: list[str] | None = None,
    red_flags: list[str] | None = None,
    target_sectors: list[str] | None = None,
) -> UserProfile:
    return UserProfile(
        username="jorge",
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=target_roles or ["ML Engineer"],
        target_sectors=target_sectors or [],
        red_flags=red_flags or [],
        location_preference=LocationPreference(modality=Modality.hybrid),
        cv_summary="Resumen.",
    )


def _make_chat_result(decision: FilterDecision) -> ChatResult:
    return ChatResult(
        content="",
        parsed=decision,
        usage=TokenUsage(
            prompt_tokens=100,
            cached_tokens=0,
            completion_tokens=20,
            total_tokens=120,
        ),
        latency_ms=50.0,
        model="gpt-4o-mini",
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def agent(mock_client: MagicMock) -> OfferFilter:
    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "system prompt"
        mock_loader.load_user.return_value = "user prompt"
        a = OfferFilter(mock_client)
        # Pre-load the system prompt so the mock is active during __init__ and calls
        a._system_prompt = "system prompt"
    return a


# ---------------------------------------------------------------------------
# Red-flag short-circuit — no LLM call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_red_flag_short_circuit_skips_llm(mock_client: MagicMock) -> None:
    agent = OfferFilter(mock_client)
    agent._system_prompt = "sys"
    mock_client.chat = AsyncMock()

    offer = _make_offer(descripcion="Buscamos comercial de ventas externo.")
    profile = _make_profile(red_flags=["comercial"])

    with patch("src.agents.offer_filter.prompt_loader"):
        decision = await agent.evaluate(offer, profile)

    assert decision.relevant is False
    assert decision.razon_descarte is not None
    assert "comercial" in decision.razon_descarte.lower()
    mock_client.chat.assert_not_called()


@pytest.mark.asyncio
async def test_red_flag_in_title_triggers_short_circuit(mock_client: MagicMock) -> None:
    agent = OfferFilter(mock_client)
    agent._system_prompt = "sys"
    mock_client.chat = AsyncMock()

    offer = _make_offer(titulo="Comercial IT Senior", descripcion="Descripción normal.")
    profile = _make_profile(red_flags=["comercial"])

    with patch("src.agents.offer_filter.prompt_loader"):
        decision = await agent.evaluate(offer, profile)

    assert decision.relevant is False
    mock_client.chat.assert_not_called()


@pytest.mark.asyncio
async def test_red_flag_updates_db_state(mock_client: MagicMock) -> None:
    agent = OfferFilter(mock_client)
    agent._system_prompt = "sys"
    mock_client.chat = AsyncMock()

    offer = _make_offer(descripcion="soporte técnico nivel 1.")
    profile = _make_profile(red_flags=["soporte"])

    with patch("src.agents.offer_filter.prompt_loader"):
        await agent.evaluate(offer, profile)

    assert offer.estado == OfferEstado.descartada
    assert offer.razon_descarte is not None


# ---------------------------------------------------------------------------
# Relevant decision via LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_relevant_decision_updates_state_to_filtrada(
    agent: OfferFilter, mock_client: MagicMock
) -> None:
    mock_client.chat = AsyncMock(return_value=_make_chat_result(FilterDecision(relevant=True)))
    offer = _make_offer()
    profile = _make_profile()

    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        decision = await agent.evaluate(offer, profile)

    assert decision.relevant is True
    assert offer.estado == OfferEstado.filtrada
    assert offer.razon_descarte is None


# ---------------------------------------------------------------------------
# Discarded decision via LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discarded_decision_updates_state_to_descartada(
    agent: OfferFilter, mock_client: MagicMock
) -> None:
    mock_client.chat = AsyncMock(
        return_value=_make_chat_result(
            FilterDecision(relevant=False, razon_descarte="Rol no compatible.")
        )
    )
    offer = _make_offer()
    profile = _make_profile()

    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        decision = await agent.evaluate(offer, profile)

    assert decision.relevant is False
    assert offer.estado == OfferEstado.descartada
    assert offer.razon_descarte == "Rol no compatible."


# ---------------------------------------------------------------------------
# LLM returns None parsed — OfferFilterError raised
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_none_parsed_raises_offer_filter_error(
    agent: OfferFilter, mock_client: MagicMock
) -> None:
    bad_result = ChatResult(
        content="",
        parsed=None,
        usage=TokenUsage(0, 0, 0, 0),
        latency_ms=10.0,
        model="gpt-4o-mini",
    )
    mock_client.chat = AsyncMock(return_value=bad_result)
    offer = _make_offer()
    profile = _make_profile()

    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        with pytest.raises(OfferFilterError):
            await agent.evaluate(offer, profile)


# ---------------------------------------------------------------------------
# evaluate_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_batch_returns_summary(agent: OfferFilter, mock_client: MagicMock) -> None:
    offers = [
        _make_offer(id=1, titulo="ML Engineer"),
        _make_offer(id=2, titulo="Data Engineer"),
        _make_offer(id=3, titulo="Soporte IT", descripcion="soporte técnico"),
    ]
    profile = _make_profile(red_flags=["soporte"])

    # First two via LLM, third via red-flag
    mock_client.chat = AsyncMock(
        side_effect=[
            _make_chat_result(FilterDecision(relevant=True)),
            _make_chat_result(FilterDecision(relevant=False, razon_descarte="Rol diferente.")),
        ]
    )

    with patch("src.agents.offer_filter.prompt_loader") as mock_loader:
        mock_loader.load_system.return_value = "sys"
        mock_loader.load_user.return_value = "usr"
        summary = await agent.evaluate_batch(offers, profile)

    assert summary.relevant_count == 1
    assert summary.discarded_count == 2
    assert summary.red_flag_count == 1
    assert len(summary.decisions) == 3
    # LLM called exactly twice (third was short-circuited)
    assert mock_client.chat.call_count == 2
