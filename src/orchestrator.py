"""Job-application pipeline orchestrator.

Chains scrape → filter → research → evaluate → write-drafts for each user.
"""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select

from src.agents.application_writer import ApplicationWriter
from src.agents.company_researcher import CompanyResearcher
from src.agents.offer_filter import OfferFilter
from src.agents.viability_evaluator import ViabilityEvaluator
from src.db.base import get_session
from src.db.enums import OfferEstado, RunEstado
from src.db.models import Company, Evaluation, Offer, RunLog, User
from src.models.evaluation import ViabilityEvaluation
from src.services import draft_persistence
from src.services.azure_openai import AzureOpenAIClient
from src.services.profiles import load_profile, upsert_user_row
from src.services.scrape_runner import run_scrape
from src.services.usage_tracker import UsageTracker

log = structlog.get_logger(__name__)


@dataclass
class RunResult:
    """Aggregated outcome of one user's pipeline run.

    Mirrors the shape of ``run_logs`` for in-memory use before persistence.
    """

    username: str
    fecha_inicio: datetime.datetime
    fecha_fin: datetime.datetime
    ofertas_scrapeadas: int
    ofertas_filtradas: int
    drafts_generados: int
    errores: list[dict[str, Any]] = field(default_factory=list)
    tokens_consumidos: dict[str, Any] = field(default_factory=dict)
    coste_estimado_eur: float = 0.0
    success: bool = True
    fatal_error: str | None = None


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _eval_from_row(ev: Evaluation) -> ViabilityEvaluation:
    contras = ev.contras if isinstance(ev.contras, dict) else {}
    return ViabilityEvaluation(
        score=ev.puntuacion,
        ventajas=list(ev.pros or []),
        desventajas=list(contras.get("desventajas", [])),
        red_flags_match=list(contras.get("red_flags_match", [])),
        recomendacion=ev.recomendacion,  # type: ignore[arg-type]
        reasoning=ev.razonamiento or "",
    )


async def run_per_offer(
    stage_name: str,
    offers: list[Offer],
    fn: Callable[[Offer], Awaitable[Any]],
    errors: list[dict[str, Any]],
    concurrency: int = 3,
) -> None:
    """Run fn(offer) for every offer with bounded concurrency; isolate per-offer errors.

    On exception: sets ``offer.estado = 'error'`` and ``offer.error_note`` with the
    exception class and message (no stack trace, no PII).
    ``KeyboardInterrupt`` and ``SystemExit`` are re-raised immediately.

    Args:
        stage_name: Label stored in the error record (``filter``, ``evaluate``, etc.).
        offers: Offer ORM objects attached to an active session.
        fn: Async callable receiving one ``Offer`` and performing the stage work.
        errors: Mutable list; error dicts are appended here on failure.
        concurrency: Max simultaneous in-flight calls (semaphore bound).
    """
    sem = asyncio.Semaphore(concurrency)

    async def _one(offer: Offer) -> None:
        async with sem:
            try:
                await fn(offer)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                offer.estado = OfferEstado.error
                offer.error_note = f"{type(exc).__name__}: {str(exc)[:200]}"
                errors.append(
                    {
                        "stage": stage_name,
                        "offer_hash": offer.hash_unico,
                        "error_class": type(exc).__name__,
                        "message": str(exc)[:200],
                    }
                )
                log.warning(
                    "per_offer_error",
                    stage=stage_name,
                    offer_id=offer.id,
                    error_class=type(exc).__name__,
                )

    await asyncio.gather(*[_one(o) for o in offers])


def _write_abort_log(
    username: str,
    fecha_inicio: datetime.datetime,
    fecha_fin: datetime.datetime,
    scraped: int,
    filtered: int,
    drafts: int,
    errors: list[dict[str, Any]],
    tracker: UsageTracker,
) -> None:
    """Persist a failed run_logs row using a fresh session.

    Called when a fatal error aborted the main session.  Failure here is
    logged but not re-raised so the orchestrator always returns a ``RunResult``.
    """
    try:
        with get_session() as session:
            user_row = session.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()
            session.add(
                RunLog(
                    user_id=user_row.id if user_row else None,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    ofertas_detectadas=scraped,
                    ofertas_relevantes=filtered,
                    borradores_generados=drafts,
                    errores=errors or None,
                    tokens_consumidos=tracker.summary() or None,
                    coste_estimado_eur=tracker.total_cost_eur() or None,
                    estado=RunEstado.failed,
                )
            )
    except Exception as exc:
        log.error("abort_log_failed", username=username, error=str(exc))


class Orchestrator:
    """Chains all agents into a complete per-user pipeline.

    Concurrency model:
    - Scraping: ``asyncio.gather`` across platforms (handled by ``run_scrape``).
    - Per-offer stages (filter, evaluate, write) and company research: bounded by a
      ``asyncio.Semaphore(concurrency)`` to cap simultaneous LLM calls.
    """

    def __init__(
        self,
        concurrency: int = 3,
        skip_stages: frozenset[str] = frozenset(),
        config_path: Path = Path("config/users"),
    ) -> None:
        self._concurrency = concurrency
        self._skip = skip_stages
        self._config_path = config_path

    def _discover_usernames(self) -> list[str]:
        return sorted(
            p.stem for p in self._config_path.glob("*.yaml") if not p.name.endswith(".example.yaml")
        )

    async def run_for_user(self, username: str) -> RunResult:
        """Run the full pipeline for one user; always returns a ``RunResult``.

        Fatal errors (LLM auth failure, DB down) are caught, logged, and written
        to ``run_logs`` with ``estado=failed`` before returning.  Only
        ``KeyboardInterrupt`` and ``SystemExit`` propagate upward.

        Args:
            username: Must match a profile YAML in ``config_path``.

        Returns:
            ``RunResult`` with stage counts, error list, token usage, and cost.
        """
        tracker = UsageTracker()
        client = AzureOpenAIClient(tracker=tracker)
        profile = load_profile(username)

        fecha_inicio = _now()
        errors: list[dict[str, Any]] = []
        scraped = 0
        filtered = 0
        draft_count: list[int] = [0]
        fatal: str | None = None
        fecha_fin = fecha_inicio

        try:
            # --- Stage 1: Scrape ---
            if "scrape" not in self._skip:
                scrape_summary = await run_scrape(profile)
                scraped = scrape_summary.written
                log.info("stage_done", stage="scrape", username=username, count=scraped)

            with get_session() as session:
                upsert_user_row(profile, session)
                session.flush()
                user_row = session.execute(
                    select(User).where(User.username == username)
                ).scalar_one()

                # --- Stage 2: Filter ---
                if "filter" not in self._skip:
                    nueva = list(
                        session.execute(
                            select(Offer)
                            .where(Offer.user_id == user_row.id)
                            .where(Offer.estado == OfferEstado.nueva)
                        ).scalars()
                    )
                    filter_agent = OfferFilter(client)

                    async def _do_filter(offer: Offer) -> None:
                        await filter_agent.evaluate(offer, profile)

                    await run_per_offer("filter", nueva, _do_filter, errors, self._concurrency)
                    filtered = sum(1 for o in nueva if o.estado == OfferEstado.filtrada)
                    log.info("stage_done", stage="filter", username=username, count=filtered)

                # --- Stage 3: Research companies ---
                if "research" not in self._skip:
                    filtrada = list(
                        session.execute(
                            select(Offer)
                            .where(Offer.user_id == user_row.id)
                            .where(Offer.estado == OfferEstado.filtrada)
                            .where(Offer.company_id.is_(None))
                        ).scalars()
                    )
                    seen_names: set[str] = set()
                    unique_names: list[str] = []
                    for o in filtrada:
                        if o.empresa not in seen_names:
                            seen_names.add(o.empresa)
                            unique_names.append(o.empresa)

                    research_agent = CompanyResearcher(client, session)
                    sem = asyncio.Semaphore(self._concurrency)

                    async def _do_research(name: str) -> None:
                        async with sem:
                            try:
                                await research_agent.research(name)
                                co_row = session.execute(
                                    select(Company).where(Company.nombre == name)
                                ).scalar_one_or_none()
                                if co_row is not None:
                                    for o in filtrada:
                                        if o.empresa == name and o.company_id is None:
                                            o.company_id = co_row.id
                                            o.estado = OfferEstado.investigada
                            except (KeyboardInterrupt, SystemExit):
                                raise
                            except Exception as exc:
                                errors.append(
                                    {
                                        "stage": "research",
                                        "company": name,
                                        "error_class": type(exc).__name__,
                                        "message": str(exc)[:200],
                                    }
                                )
                                log.warning(
                                    "research_error",
                                    company=name,
                                    error=str(exc)[:100],
                                )

                    await asyncio.gather(*[_do_research(n) for n in unique_names])
                    log.info(
                        "stage_done",
                        stage="research",
                        username=username,
                        count=len(unique_names),
                    )

                # --- Stage 4: Evaluate ---
                if "evaluate" not in self._skip:
                    investig = list(
                        session.execute(
                            select(Offer)
                            .where(Offer.user_id == user_row.id)
                            .where(
                                Offer.estado.in_([OfferEstado.investigada, OfferEstado.filtrada])
                            )
                            .where(Offer.company_id.is_not(None))
                        ).scalars()
                    )
                    eval_agent = ViabilityEvaluator(client, session)

                    async def _do_eval(offer: Offer) -> None:
                        co_row = session.get(Company, offer.company_id)
                        if co_row is None:
                            return
                        await eval_agent.evaluate(offer, co_row, profile)

                    await run_per_offer("evaluate", investig, _do_eval, errors, self._concurrency)
                    log.info("stage_done", stage="evaluate", username=username)

                # --- Stage 5: Write drafts ---
                if "write" not in self._skip:
                    evaluada = list(
                        session.execute(
                            select(Offer)
                            .join(Evaluation, Evaluation.offer_id == Offer.id)
                            .where(Offer.user_id == user_row.id)
                            .where(Offer.estado == OfferEstado.evaluada)
                            .where(Evaluation.recomendacion.in_(["aplicar", "dudar"]))
                        ).scalars()
                    )
                    writer = ApplicationWriter(client)

                    async def _do_write(offer: Offer) -> None:
                        co_row = session.get(Company, offer.company_id)
                        if co_row is None:
                            return
                        ev_row = offer.evaluation
                        if ev_row is None:
                            return
                        evaluation = _eval_from_row(ev_row)
                        draft = await writer.write(offer, co_row, evaluation, profile)
                        draft_persistence.save_draft(draft, offer, profile, session)
                        draft_count[0] += 1

                    await run_per_offer("write", evaluada, _do_write, errors, self._concurrency)
                    log.info(
                        "stage_done",
                        stage="write",
                        username=username,
                        count=draft_count[0],
                    )

                # --- Persist run log (committed with the session) ---
                fecha_fin = _now()
                session.add(
                    RunLog(
                        user_id=user_row.id,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin,
                        ofertas_detectadas=scraped,
                        ofertas_relevantes=filtered,
                        borradores_generados=draft_count[0],
                        errores=errors or None,
                        tokens_consumidos=tracker.summary() or None,
                        coste_estimado_eur=tracker.total_cost_eur() or None,
                        estado=RunEstado.completed,
                    )
                )

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            fatal = f"{type(exc).__name__}: {str(exc)[:300]}"
            errors.append(
                {
                    "stage": "fatal",
                    "error_class": type(exc).__name__,
                    "message": str(exc)[:300],
                }
            )
            log.error("orchestrator_fatal", username=username, error=fatal)
            fecha_fin = _now()
            _write_abort_log(
                username,
                fecha_inicio,
                fecha_fin,
                scraped,
                filtered,
                draft_count[0],
                errors,
                tracker,
            )

        return RunResult(
            username=username,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ofertas_scrapeadas=scraped,
            ofertas_filtradas=filtered,
            drafts_generados=draft_count[0],
            errores=errors,
            tokens_consumidos=tracker.summary(),
            coste_estimado_eur=tracker.total_cost_eur(),
            success=fatal is None,
            fatal_error=fatal,
        )

    async def run_for_all_users(self) -> list[RunResult]:
        """Run the pipeline sequentially for every user discovered in ``config_path``.

        Returns:
            One ``RunResult`` per user, in alphabetical username order.
        """
        results: list[RunResult] = []
        for username in self._discover_usernames():
            result = await self.run_for_user(username)
            results.append(result)
        return results
