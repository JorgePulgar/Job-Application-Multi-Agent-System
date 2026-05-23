"""CompanyResearcher agent: web search + gpt-4o synthesis → CompanyDossier."""

from __future__ import annotations

import asyncio
import datetime

import structlog
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company
from src.exceptions import JobAgentError
from src.models.company import CompanyDossier, TamanoEmpresa
from src.models.search import SearchResult
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient
from src.services.web_search import search_web

logger = structlog.get_logger(__name__)

_RESULTS_PER_QUERY: int = 3
_DEFAULT_TTL_DAYS: int = 30

_SEARCH_TEMPLATES: list[str] = [
    '"{name}" empresa',
    '"{name}" site:linkedin.com/company',
    '"{name}" reseñas glassdoor',
    '"{name}" stack tecnológico',
    '"{name}" news',
]

_QUERY_LABELS: list[str] = ["empresa", "linkedin", "glassdoor", "stack", "news"]


class CompanyResearchError(JobAgentError):
    """Raised when company research fails after retries are exhausted."""


class _ResearchOutput(BaseModel):
    """LLM-facing structured output — excludes fuentes (populated from search results)."""

    sector: str
    tamano: TamanoEmpresa
    ubicacion_hq: str
    descripcion: str
    stack_tecnologico: list[str]
    cultura_notas: list[str]
    red_flags_detectadas: list[str]
    productos_o_servicios: list[str]
    equipo_ai_detectado: bool


def _format_search_results(
    all_results: list[list[SearchResult]],
    labels: list[str],
) -> str:
    """Format search results as a markdown block for the user prompt.

    Args:
        all_results: One list of results per query.
        labels: Human-readable label for each query (same order).

    Returns:
        Markdown string with titled sections per query.
    """
    sections: list[str] = []
    for label, results in zip(labels, all_results, strict=True):
        if not results:
            continue
        lines = [f"### {label}"]
        for r in results[:_RESULTS_PER_QUERY]:
            lines.append(f"- **{r.title}**: {r.snippet}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections) if sections else "Sin resultados de búsqueda."


def _collect_source_urls(all_results: list[list[SearchResult]]) -> list[str]:
    """Deduplicate source URLs across all search result lists.

    Args:
        all_results: One list of results per query.

    Returns:
        Ordered, deduplicated list of URL strings.
    """
    seen: set[str] = set()
    urls: list[str] = []
    for results in all_results:
        for r in results[:_RESULTS_PER_QUERY]:
            if r.url and r.url not in seen:
                seen.add(r.url)
                urls.append(r.url)
    return urls


class CompanyResearcher:
    """Research a company via web search and synthesise a CompanyDossier with gpt-4o.

    The agent is intentionally stateless between calls — each ``research()`` call
    is independent.  The session is owned by the caller; this agent only flushes,
    never commits.
    """

    def __init__(self, client: AzureOpenAIClient, session: AsyncSession) -> None:
        self._client = client
        self._session = session
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = prompt_loader.load_system("company_researcher")
        return self._system_prompt

    async def research(self, company_name: str) -> CompanyDossier:
        """Research a company and persist the dossier to the ``companies`` table.

        Issues 5 concurrent web search queries, pipes the top results into gpt-4o,
        and stores the structured dossier with a 30-day TTL.

        Args:
            company_name: Company name as it appears in the job offer.

        Returns:
            Synthesised ``CompanyDossier``.

        Raises:
            CompanyResearchError: If the LLM returns an unparseable response.
        """
        log = logger.bind(company=company_name)
        log.info("company_research_start")

        queries = [t.format(name=company_name) for t in _SEARCH_TEMPLATES]
        all_results: list[list[SearchResult]] = await asyncio.gather(
            *[search_web(q, n=_RESULTS_PER_QUERY) for q in queries]
        )

        search_block = _format_search_results(all_results, _QUERY_LABELS)
        source_urls = _collect_source_urls(all_results)

        system = self._get_system_prompt()
        user = prompt_loader.load_user(
            "company_researcher",
            company_name=company_name,
            search_results=search_block,
        )

        result = await self._client.chat(
            deployment="4o",
            system=system,
            user=user,
            response_format=_ResearchOutput,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, _ResearchOutput):
            raise CompanyResearchError(
                f"LLM did not return a valid _ResearchOutput for company '{company_name}'"
            )

        raw: _ResearchOutput = result.parsed

        dossier = CompanyDossier(
            sector=raw.sector,
            tamano=raw.tamano,
            ubicacion_hq=raw.ubicacion_hq,
            descripcion=raw.descripcion,
            stack_tecnologico=raw.stack_tecnologico,
            cultura_notas=raw.cultura_notas,
            red_flags_detectadas=raw.red_flags_detectadas,
            productos_o_servicios=raw.productos_o_servicios,
            equipo_ai_detectado=raw.equipo_ai_detectado,
            fuentes=source_urls,  # type: ignore[arg-type]
        )

        await self._upsert_company(company_name, dossier)

        log.info(
            "company_research_done",
            tamano=dossier.tamano,
            ai_team=dossier.equipo_ai_detectado,
            tokens=result.usage.total_tokens,
        )
        return dossier

    async def _upsert_company(self, nombre: str, dossier: CompanyDossier) -> None:
        """Insert or update the companies row with the new dossier and TTL.

        Args:
            nombre: Company name used as the lookup key.
            dossier: Freshly researched dossier to persist.
        """
        now = datetime.datetime.now(datetime.UTC)
        expira_en = now + datetime.timedelta(days=_DEFAULT_TTL_DAYS)

        result = await self._session.execute(select(Company).where(Company.nombre == nombre))
        company = result.scalar_one_or_none()

        dossier_dict = dossier.model_dump(mode="json")

        if company is None:
            company = Company(
                nombre=nombre,
                sector=dossier.sector,
                descripcion=dossier.descripcion,
                dossier_json=dossier_dict,
                fecha_research=now,
                expira_en=expira_en,
            )
            self._session.add(company)
            logger.debug("company_row_created", nombre=nombre)
        else:
            company.sector = dossier.sector
            company.descripcion = dossier.descripcion
            company.dossier_json = dossier_dict
            company.fecha_research = now
            company.expira_en = expira_en
            company.updated_at = now
            logger.debug("company_row_updated", nombre=nombre)

        await self._session.flush()
