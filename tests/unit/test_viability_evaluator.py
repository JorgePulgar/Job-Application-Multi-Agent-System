"""Unit tests for src/agents/viability_evaluator.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.viability_evaluator import ViabilityEvaluator, ViabilityEvaluatorError
from src.db.enums import OfferEstado
from src.db.models import Evaluation as DbEvaluation
from src.models.evaluation import ViabilityEvaluation
from src.services.azure_openai import ChatResult, TokenUsage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evaluation(
    *,
    score: int = 80,
    ventajas: list[str] | None = None,
    desventajas: list[str] | None = None,
    red_flags_match: list[str] | None = None,
    recomendacion: str = "aplicar",
    reasoning: str = "Buen encaje técnico y sectorial.",
) -> ViabilityEvaluation:
    return ViabilityEvaluation(
        score=score,
        ventajas=ventajas or ["Stack alineado", "Sector objetivo"],
        desventajas=desventajas or [],
        red_flags_match=red_flags_match or [],
        recomendacion=recomendacion,  # type: ignore[arg-type]
        reasoning=reasoning,
    )


def _make_chat_result(parsed: ViabilityEvaluation | None) -> ChatResult:
    return ChatResult(
        content="",
        parsed=parsed,
        usage=TokenUsage(
            prompt_tokens=600, cached_tokens=300, completion_tokens=200, total_tokens=800
        ),
        latency_ms=900.0,
        model="gpt-4o",
    )


def _make_offer(
    *,
    offer_id: int = 1,
    titulo: str = "ML Engineer",
    empresa: str = "Acme Corp",
    ubicacion: str = "Madrid",
    descripcion: str = "Desarrollar modelos de ML en producción.",
    estado: str = OfferEstado.investigada,
    raw_json: dict[str, object] | None = None,
) -> MagicMock:
    offer = MagicMock()
    offer.id = offer_id
    offer.titulo = titulo
    offer.empresa = empresa
    offer.ubicacion = ubicacion
    offer.descripcion = descripcion
    offer.estado = estado
    offer.raw_json = raw_json or {}
    return offer


def _make_company(*, nombre: str = "Acme Corp", dossier_json: object = None) -> MagicMock:
    company = MagicMock()
    company.nombre = nombre
    company.dossier_json = dossier_json
    return company


def _make_profile() -> MagicMock:
    profile = MagicMock()
    profile.target_roles = ["ML Engineer", "Data Scientist"]
    profile.target_sectors = ["fintech", "saas"]
    profile.tech_stack = ["Python", "TensorFlow", "Kubernetes"]
    profile.min_salary = 45000
    profile.red_flags = ["comercial", "soporte", "presencial obligatorio"]
    profile.location_preference.modality = "remote"
    return profile


def _make_session() -> MagicMock:
    return MagicMock()


def _make_agent(parsed: ViabilityEvaluation | None = None) -> tuple[ViabilityEvaluator, MagicMock]:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(parsed or _make_evaluation()))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system prompt"
    return agent, session


# ---------------------------------------------------------------------------
# Happy path — returns ViabilityEvaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_returns_viability_evaluation() -> None:
    evaluation = _make_evaluation(score=75)
    agent, _ = _make_agent(parsed=evaluation)

    with patch("src.agents.viability_evaluator.prompt_loader"):
        result = await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    assert isinstance(result, ViabilityEvaluation)
    assert result.score == 75


@pytest.mark.asyncio
async def test_evaluate_uses_gpt4o_deployment() -> None:
    evaluation = _make_evaluation()
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(evaluation))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    with patch("src.agents.viability_evaluator.prompt_loader"):
        await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    call_kwargs = client.chat.call_args.kwargs
    assert call_kwargs["deployment"] == "4o"


@pytest.mark.asyncio
async def test_evaluate_enables_caching() -> None:
    evaluation = _make_evaluation()
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(evaluation))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    with patch("src.agents.viability_evaluator.prompt_loader"):
        await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    assert client.chat.call_args.kwargs["cacheable_system"] is True


# ---------------------------------------------------------------------------
# DB persistence — row created, offer estado updated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_adds_evaluation_row_to_session() -> None:
    agent, session = _make_agent()

    with patch("src.agents.viability_evaluator.prompt_loader"):
        await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    session.add.assert_called_once()
    added = session.add.call_args[0][0]
    assert isinstance(added, DbEvaluation)


@pytest.mark.asyncio
async def test_evaluate_flushes_session() -> None:
    agent, session = _make_agent()

    with patch("src.agents.viability_evaluator.prompt_loader"):
        await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_sets_offer_estado_to_evaluada() -> None:
    agent, _ = _make_agent()
    offer = _make_offer(estado=OfferEstado.investigada)

    with patch("src.agents.viability_evaluator.prompt_loader"):
        await agent.evaluate(offer, _make_company(), _make_profile())

    assert offer.estado == OfferEstado.evaluada


@pytest.mark.asyncio
async def test_evaluate_db_row_fields_correct() -> None:
    evaluation = _make_evaluation(
        score=82,
        ventajas=["Stack Python", "Sector fintech"],
        desventajas=["Salario no especificado"],
        red_flags_match=[],
        recomendacion="aplicar",
        reasoning="Buen encaje.",
    )
    agent, session = _make_agent(parsed=evaluation)
    offer = _make_offer(offer_id=42)

    with patch("src.agents.viability_evaluator.prompt_loader"):
        await agent.evaluate(offer, _make_company(), _make_profile())

    added: DbEvaluation = session.add.call_args[0][0]
    assert added.offer_id == 42
    assert added.puntuacion == 82
    assert added.pros == ["Stack Python", "Sector fintech"]
    assert added.contras == {"desventajas": ["Salario no especificado"], "red_flags_match": []}
    assert added.recomendacion == "aplicar"
    assert added.razonamiento == "Buen encaje."


# ---------------------------------------------------------------------------
# Cross-field rule: red_flags_match + descartar/dudar (not aplicar)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_with_red_flags_and_descartar() -> None:
    evaluation = _make_evaluation(
        score=20,
        red_flags_match=["presencial obligatorio"],
        recomendacion="descartar",
    )
    agent, session = _make_agent(parsed=evaluation)

    with patch("src.agents.viability_evaluator.prompt_loader"):
        result = await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    assert result.recomendacion == "descartar"
    assert result.red_flags_match == ["presencial obligatorio"]
    added: DbEvaluation = session.add.call_args[0][0]
    assert added.contras["red_flags_match"] == ["presencial obligatorio"]


@pytest.mark.asyncio
async def test_evaluate_with_red_flags_and_dudar() -> None:
    evaluation = _make_evaluation(
        score=45,
        red_flags_match=["soporte"],
        recomendacion="dudar",
    )
    agent, _ = _make_agent(parsed=evaluation)

    with patch("src.agents.viability_evaluator.prompt_loader"):
        result = await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    assert result.recomendacion == "dudar"


# ---------------------------------------------------------------------------
# LLM returns None → ViabilityEvaluatorError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_raises_on_null_parsed() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(None))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    with (
        patch("src.agents.viability_evaluator.prompt_loader"),
        pytest.raises(ViabilityEvaluatorError, match="ViabilityEvaluation"),
    ):
        await agent.evaluate(_make_offer(), _make_company(), _make_profile())


@pytest.mark.asyncio
async def test_evaluate_raises_does_not_flush_on_error() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(None))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    with (
        patch("src.agents.viability_evaluator.prompt_loader"),
        pytest.raises(ViabilityEvaluatorError),
    ):
        await agent.evaluate(_make_offer(), _make_company(), _make_profile())

    session.add.assert_not_called()
    session.flush.assert_not_called()


# ---------------------------------------------------------------------------
# Dossier summary — missing / invalid dossier_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_handles_missing_dossier_json() -> None:
    """Agent should not crash when company has no dossier_json."""
    evaluation = _make_evaluation()
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(evaluation))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    company = _make_company(dossier_json=None)
    captured: list[str] = []

    def fake_load_user(name: str, **kwargs: str) -> str:
        captured.append(kwargs.get("dossier", ""))
        return "user prompt"

    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_user.side_effect = fake_load_user
        await agent.evaluate(_make_offer(), company, _make_profile())

    assert captured and "Sin dossier" in captured[0]


@pytest.mark.asyncio
async def test_evaluate_handles_invalid_dossier_json() -> None:
    """Agent should fall back gracefully on corrupt dossier_json."""
    evaluation = _make_evaluation()
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(evaluation))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    company = _make_company(dossier_json={"not": "a valid dossier"})
    captured: list[str] = []

    def fake_load_user(name: str, **kwargs: str) -> str:
        captured.append(kwargs.get("dossier", ""))
        return "user prompt"

    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_user.side_effect = fake_load_user
        await agent.evaluate(_make_offer(), company, _make_profile())

    assert captured and "error de formato" in captured[0]


# ---------------------------------------------------------------------------
# Salary extraction from raw_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_extracts_salary_from_raw_json() -> None:
    evaluation = _make_evaluation()
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(evaluation))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    offer = _make_offer(raw_json={"salary_min": 50000})
    captured: list[str] = []

    def fake_load_user(name: str, **kwargs: str) -> str:
        captured.append(kwargs.get("salario", ""))
        return "user prompt"

    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_user.side_effect = fake_load_user
        await agent.evaluate(offer, _make_company(), _make_profile())

    assert captured and captured[0] == "50000"


@pytest.mark.asyncio
async def test_evaluate_salary_fallback_when_absent() -> None:
    evaluation = _make_evaluation()
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(evaluation))
    session = _make_session()
    agent = ViabilityEvaluator(client, session)
    agent._system_prompt = "system"

    offer = _make_offer(raw_json={})
    captured: list[str] = []

    def fake_load_user(name: str, **kwargs: str) -> str:
        captured.append(kwargs.get("salario", ""))
        return "user prompt"

    with patch("src.agents.viability_evaluator.prompt_loader") as mock_loader:
        mock_loader.load_user.side_effect = fake_load_user
        await agent.evaluate(offer, _make_company(), _make_profile())

    assert captured and captured[0] == "No especificado"
