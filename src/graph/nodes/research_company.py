"""``research_company`` fan-out branch: produce a ``CompanyDossier``.

Reuses the existing ``CompanyResearcher`` agent verbatim -- including its
``companies``-table TTL cache, so a company already researched today is reused
rather than re-searched. Does not reimplement research or web search.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager

import structlog
from sqlalchemy.orm import Session

from src.agents.company_researcher import CompanyResearcher
from src.db.base import get_session
from src.graph.state import EvaluateDraftState
from src.models.company import CompanyDossier
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], AbstractContextManager[Session]]
ResearchCompanyNode = Callable[[EvaluateDraftState], Awaitable[dict[str, CompanyDossier]]]


def make_research_company(
    client: AzureOpenAIClient,
    session_factory: SessionFactory = get_session,
) -> ResearchCompanyNode:
    """Build the ``research_company`` node bound to its dependencies.

    Args:
        client: Azure OpenAI client passed to ``CompanyResearcher``.
        session_factory: Callable yielding a context-managed ``Session`` (the
            researcher reads/writes the ``companies`` cache through it).

    Returns:
        The ``research_company`` coroutine LangGraph invokes.
    """

    async def research_company(state: EvaluateDraftState) -> dict[str, CompanyDossier]:
        """Research the offer's company (cache-aware) into a dossier.

        Args:
            state: Graph state carrying ``parsed`` (for the company name).

        Returns:
            ``{"dossier": CompanyDossier}``.
        """
        company_name = state["parsed"].company
        with session_factory() as session:
            researcher = CompanyResearcher(client, session)
            dossier = await researcher.research(company_name)
        logger.info("graph_research_company_done", company=company_name)
        return {"dossier": dossier}

    return research_company
