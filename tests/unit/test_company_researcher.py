"""Unit tests for src/agents/company_researcher.py."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.company_researcher import (
    CompanyResearcher,
    CompanyResearchError,
    _collect_source_urls,
    _format_search_results,
    _ResearchOutput,
)
from src.models.company import TamanoEmpresa
from src.models.search import SearchResult
from src.services.azure_openai import ChatResult, TokenUsage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_search_results(base_url: str, n: int = 2) -> list[SearchResult]:
    return [
        SearchResult(title=f"Title {i}", url=f"{base_url}/{i}", snippet=f"Snippet {i}")
        for i in range(n)
    ]


def _make_raw_output() -> _ResearchOutput:
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


def _make_chat_result(parsed: _ResearchOutput) -> ChatResult:
    return ChatResult(
        content="",
        parsed=parsed,
        usage=TokenUsage(
            prompt_tokens=500, cached_tokens=200, completion_tokens=150, total_tokens=650
        ),
        latency_ms=800.0,
        model="gpt-4o",
    )


def _make_session(existing_company: object = None) -> AsyncMock:
    """Return a mock AsyncSession whose execute chain returns existing_company."""
    session = AsyncMock()
    session.add = MagicMock()  # add() is sync in SQLAlchemy
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = existing_company
    session.execute.return_value = exec_result
    return session


# ---------------------------------------------------------------------------
# _format_search_results
# ---------------------------------------------------------------------------


def test_format_search_results_produces_sections() -> None:
    results = [[SearchResult(title="T", url="https://a.com", snippet="S")]]
    text = _format_search_results(results, ["empresa"])
    assert "### empresa" in text
    assert "T" in text
    assert "S" in text


def test_format_search_results_empty_list_returns_fallback() -> None:
    text = _format_search_results([[]], ["empresa"])
    assert "Sin resultados" in text


def test_format_search_results_skips_empty_queries() -> None:
    results = [[], [SearchResult(title="X", url="https://b.com", snippet="Y")]]
    text = _format_search_results(results, ["a", "b"])
    assert "### a" not in text
    assert "### b" in text


# ---------------------------------------------------------------------------
# _collect_source_urls
# ---------------------------------------------------------------------------


def test_collect_source_urls_deduplicates() -> None:
    r1 = [SearchResult(title="A", url="https://dup.com", snippet="s")]
    r2 = [SearchResult(title="B", url="https://dup.com", snippet="s")]
    urls = _collect_source_urls([r1, r2])
    assert urls == ["https://dup.com"]


def test_collect_source_urls_preserves_order() -> None:
    r1 = [SearchResult(title="A", url="https://a.com", snippet="s")]
    r2 = [SearchResult(title="B", url="https://b.com", snippet="s")]
    urls = _collect_source_urls([r1, r2])
    assert urls == ["https://a.com", "https://b.com"]


# ---------------------------------------------------------------------------
# research() — happy path (new company)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_issues_five_queries() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session()

    fake_results = _make_search_results("https://example.com", n=2)

    with (
        patch("src.agents.company_researcher.search_web", return_value=fake_results) as mock_sw,
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")

    assert mock_sw.call_count == 5


@pytest.mark.asyncio
async def test_research_queries_include_company_name() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session()

    captured_queries: list[str] = []

    async def fake_search(query: str, n: int = 10) -> list[SearchResult]:
        captured_queries.append(query)
        return []

    with (
        patch("src.agents.company_researcher.search_web", side_effect=fake_search),
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")

    assert all("Acme Corp" in q for q in captured_queries)
    assert len(captured_queries) == 5


@pytest.mark.asyncio
async def test_research_returns_company_dossier() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session()

    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        dossier = await agent.research("Acme Corp")

    from src.models.company import CompanyDossier

    assert isinstance(dossier, CompanyDossier)
    assert dossier.sector == "fintech"
    assert dossier.equipo_ai_detectado is True


@pytest.mark.asyncio
async def test_research_upserts_new_company_row() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session(existing_company=None)

    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")

    session.add.assert_called_once()
    session.flush.assert_awaited_once()

    added = session.add.call_args[0][0]
    from src.db.models import Company

    assert isinstance(added, Company)
    assert added.nombre == "Acme Corp"
    assert added.sector == "fintech"


@pytest.mark.asyncio
async def test_research_expira_en_is_30_days_out() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session(existing_company=None)

    before = datetime.datetime.now(datetime.UTC)

    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")

    after = datetime.datetime.now(datetime.UTC)
    added = session.add.call_args[0][0]

    expected_low = before + datetime.timedelta(days=30)
    expected_high = after + datetime.timedelta(days=30)
    assert expected_low <= added.expira_en <= expected_high


# ---------------------------------------------------------------------------
# research() — existing company (update path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_updates_existing_company_row() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))

    existing = MagicMock()
    existing.nombre = "Acme Corp"
    session = _make_session(existing_company=existing)

    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")

    session.add.assert_not_called()
    session.flush.assert_awaited_once()
    assert existing.sector == "fintech"
    assert existing.expira_en is not None


# ---------------------------------------------------------------------------
# research() — LLM returns None parsed → CompanyResearchError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_raises_on_null_parsed() -> None:
    from src.services.azure_openai import ChatResult, TokenUsage

    bad_result = ChatResult(
        content="",
        parsed=None,
        usage=TokenUsage(0, 0, 0, 0),
        latency_ms=10.0,
        model="gpt-4o",
    )
    client = MagicMock()
    client.chat = AsyncMock(return_value=bad_result)
    session = _make_session()

    with (
        patch("src.agents.company_researcher.search_web", return_value=[]),
        patch("src.agents.company_researcher.prompt_loader"),
        pytest.raises(CompanyResearchError),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")


# ---------------------------------------------------------------------------
# research() — search results populated into prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_passes_search_results_to_prompt() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session()

    fake_results = [
        SearchResult(title="Acme Home", url="https://acme.com", snippet="Acme builds payments.")
    ]

    captured_user_prompt: list[str] = []

    def fake_load_user(name: str, **kwargs: str) -> str:
        captured_user_prompt.append(kwargs.get("search_results", ""))
        return "user prompt"

    with (
        patch("src.agents.company_researcher.search_web", return_value=fake_results),
        patch("src.agents.company_researcher.prompt_loader") as mock_loader,
    ):
        mock_loader.load_system.return_value = "system"
        mock_loader.load_user.side_effect = fake_load_user
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        await agent.research("Acme Corp")

    assert len(captured_user_prompt) == 1
    assert "Acme builds payments." in captured_user_prompt[0]


# ---------------------------------------------------------------------------
# research() — source URLs from search results added to dossier fuentes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_populates_fuentes_from_search_results() -> None:
    client = MagicMock()
    client.chat = AsyncMock(return_value=_make_chat_result(_make_raw_output()))
    session = _make_session()

    fake_results = [SearchResult(title="T", url="https://source.example.com", snippet="S")]

    with (
        patch("src.agents.company_researcher.search_web", return_value=fake_results),
        patch("src.agents.company_researcher.prompt_loader"),
    ):
        agent = CompanyResearcher(client, session)
        agent._system_prompt = "system"
        dossier = await agent.research("Acme Corp")

    assert any("source.example.com" in str(f) for f in dossier.fuentes)
