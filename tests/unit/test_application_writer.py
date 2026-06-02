"""Unit tests for src/agents/application_writer.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.application_writer import ApplicationWriter, ApplicationWriterError
from src.models.draft import Draft
from src.models.evaluation import ViabilityEvaluation
from src.models.user_profile import (
    Experience,
    LocationPreference,
    Modality,
    UserProfile,
)
from src.services.azure_openai import ChatResult, TokenUsage

_BODY = (
    "Estimado equipo de Acme, tras leer que habéis lanzado vuestra plataforma de "
    "datos en tiempo real me dirijo a vosotros. Mi experiencia construyendo "
    "pipelines de datos encaja con ese reto y me gustaría aportar al equipo."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_draft(*, needs_manual_context: bool = False) -> Draft:
    if needs_manual_context:
        return Draft(
            email_subject="",
            email_body="",
            needs_manual_context=True,
            flagged_reasons=["no_specific_hook"],
            experiencias_destacadas=["a", "b", "c"],
        )
    return Draft(
        email_subject="Candidatura: ML Engineer en Acme",
        email_body=_BODY,
        carta_presentacion="## Carta\n\nContenido relevante.",
        experiencias_destacadas=[
            "5 años en pipelines de datos",
            "Migración a Azure",
            "Mentoría de juniors",
        ],
    )


def _make_chat_result(parsed: Draft | None) -> ChatResult:
    return ChatResult(
        content="",
        parsed=parsed,
        usage=TokenUsage(
            prompt_tokens=1200, cached_tokens=900, completion_tokens=400, total_tokens=1600
        ),
        latency_ms=1100.0,
        model="gpt-4o",
    )


def _make_offer() -> MagicMock:
    offer = MagicMock()
    offer.id = 7
    offer.titulo = "ML Engineer"
    offer.empresa = "Acme Corp"
    offer.ubicacion = "Madrid"
    offer.descripcion = "Construir y desplegar modelos de ML en producción."
    return offer


def _make_company(*, dossier_json: object = None) -> MagicMock:
    company = MagicMock()
    company.nombre = "Acme Corp"
    company.dossier_json = dossier_json
    return company


def _make_evaluation() -> ViabilityEvaluation:
    return ViabilityEvaluation(
        score=80,
        ventajas=["Stack alineado", "Sector objetivo"],
        desventajas=["Salario no especificado"],
        red_flags_match=[],
        recomendacion="aplicar",
        reasoning="Buen encaje.",
    )


def _make_profile() -> UserProfile:
    return UserProfile(
        username="jorge",
        nombre="Jorge Pulgar",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["ML Engineer", "Data Engineer"],
        tech_stack=["Python", "Azure"],
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="Ingeniero de datos con experiencia en MLOps.",
        experiences=[
            Experience(
                company="DataCo",
                role="Data Engineer",
                start_date="2020",
                achievements=["Construí pipelines en Azure"],
                technologies=["Python", "Spark"],
            )
        ],
    )


def _make_agent(parsed: Draft | None = None) -> tuple[ApplicationWriter, MagicMock]:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(parsed or _make_draft()))
    agent = ApplicationWriter(client)
    return agent, client


# ---------------------------------------------------------------------------
# Happy path — returns Draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_returns_draft() -> None:
    agent, _ = _make_agent()
    result = await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert isinstance(result, Draft)
    assert result.email_subject == "Candidatura: ML Engineer en Acme"


@pytest.mark.asyncio
async def test_write_returns_flagged_draft() -> None:
    agent, _ = _make_agent(parsed=_make_draft(needs_manual_context=True))
    result = await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert result.needs_manual_context is True
    assert result.flagged_reasons == ["no_specific_hook"]


# ---------------------------------------------------------------------------
# Deployment + caching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_uses_gpt4o_deployment() -> None:
    agent, client = _make_agent()
    await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert client.chat.call_args.kwargs["deployment"] == "4o"


@pytest.mark.asyncio
async def test_write_enables_caching() -> None:
    agent, client = _make_agent()
    await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert client.chat.call_args.kwargs["cacheable_system"] is True


@pytest.mark.asyncio
async def test_write_uses_draft_response_format() -> None:
    agent, client = _make_agent()
    await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert client.chat.call_args.kwargs["response_format"] is Draft


# ---------------------------------------------------------------------------
# CV is included in the system message (prompt-caching primary use case)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_includes_cv_in_system_message() -> None:
    agent, client = _make_agent()
    profile = _make_profile()

    await agent.write(_make_offer(), _make_company(), _make_evaluation(), profile)

    system = client.chat.call_args.kwargs["system"]
    # CV markers rendered by cv_for_prompt() must appear in the system prompt.
    assert "Jorge Pulgar" in system
    assert "Ingeniero de datos con experiencia en MLOps." in system
    assert "DataCo" in system


@pytest.mark.asyncio
async def test_write_user_message_has_offer_and_evaluation() -> None:
    agent, client = _make_agent()
    await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())

    user = client.chat.call_args.kwargs["user"]
    assert "ML Engineer" in user
    assert "Acme Corp" in user
    assert "Stack alineado" in user  # ventaja
    assert "Salario no especificado" in user  # desventaja


# ---------------------------------------------------------------------------
# Dossier handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_handles_missing_dossier() -> None:
    agent, client = _make_agent()
    await agent.write(
        _make_offer(), _make_company(dossier_json=None), _make_evaluation(), _make_profile()
    )
    user = client.chat.call_args.kwargs["user"]
    assert "Sin dossier" in user


@pytest.mark.asyncio
async def test_write_handles_invalid_dossier() -> None:
    agent, client = _make_agent()
    await agent.write(
        _make_offer(),
        _make_company(dossier_json={"not": "valid"}),
        _make_evaluation(),
        _make_profile(),
    )
    user = client.chat.call_args.kwargs["user"]
    assert "error de formato" in user


@pytest.mark.asyncio
async def test_write_empty_evaluation_cons_renders_placeholder() -> None:
    agent, client = _make_agent()
    evaluation = ViabilityEvaluation(
        score=80,
        ventajas=["Stack alineado"],
        desventajas=[],
        red_flags_match=[],
        recomendacion="aplicar",
        reasoning="Buen encaje.",
    )
    await agent.write(_make_offer(), _make_company(), evaluation, _make_profile())
    user = client.chat.call_args.kwargs["user"]
    assert "(ninguno)" in user


# ---------------------------------------------------------------------------
# LLM returns None → ApplicationWriterError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_raises_on_null_parsed() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(None))
    agent = ApplicationWriter(client)

    with pytest.raises(ApplicationWriterError, match="Draft"):
        await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())


def test_writer_holds_no_session() -> None:
    """Generation only — persistence (and estado transition) is Task 05."""
    agent = ApplicationWriter(MagicMock())
    assert not hasattr(agent, "_session")


# ---------------------------------------------------------------------------
# Signature appended deterministically (not generated by the model)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_appends_signature_to_body() -> None:
    agent, _ = _make_agent()
    profile = _make_profile()

    result = await agent.write(_make_offer(), _make_company(), _make_evaluation(), profile)

    assert result.email_body.startswith(_BODY)
    assert profile.signature_html() in result.email_body
    assert "Jorge Pulgar" in result.email_body
    assert "jorge@example.com" in result.email_body


@pytest.mark.asyncio
async def test_write_does_not_append_signature_when_flagged() -> None:
    agent, _ = _make_agent(parsed=_make_draft(needs_manual_context=True))
    result = await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert result.email_body == ""


@pytest.mark.asyncio
async def test_write_body_has_no_dashes_from_signature() -> None:
    agent, _ = _make_agent()
    result = await agent.write(_make_offer(), _make_company(), _make_evaluation(), _make_profile())
    assert "—" not in result.email_body
    assert "–" not in result.email_body  # noqa: RUF001
