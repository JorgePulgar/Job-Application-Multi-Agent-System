"""Job-application pipeline orchestrator.

Chains scrape → filter → research → evaluate → write-drafts for each user.
"""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agents.application_writer import ApplicationWriter
from src.agents.company_researcher import CompanyResearcher
from src.agents.offer_filter import OfferFilter
from src.agents.viability_evaluator import ViabilityEvaluator
from src.config import get_settings
from src.db.base import get_session
from src.db.enums import OfferEstado, RunEstado
from src.db.models import Company, Evaluation, Offer, RunLog, User
from src.models.evaluation import ViabilityEvaluation
from src.models.fit import CoverLetterDraft, FitAssessment
from src.models.user_profile import UserProfile
from src.services import draft_persistence, telegram
from src.services.azure_openai import AzureOpenAIClient
from src.services.profiles import load_profile, upsert_user_row
from src.services.scrape_runner import run_scrape
from src.services.telegram import escape_markdown_v2
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
    ofertas_descartadas: int = 0
    ofertas_investigadas: int = 0
    ofertas_evaluadas: int = 0
    drafts_manual_context: int = 0
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


def _upsert_evaluation(session: Session, offer: Offer, fit: FitAssessment) -> None:
    """Write or replace the ``evaluations`` row for an offer from a graph FitAssessment.

    Mirrors the v1 evaluator's persistence semantics: sets ``offer.estado`` to
    ``evaluada`` and records ``razon_descarte`` on a skip verdict. Idempotent on
    ``offer_id`` so a re-processed offer updates its row instead of violating the
    unique constraint.

    Args:
        session: Active session owned by the caller.
        offer: The offer being evaluated (attached to ``session``).
        fit: The graph's fit assessment to persist.
    """
    row = fit.to_evaluation_row(offer.id)
    existing = session.scalars(select(Evaluation).where(Evaluation.offer_id == offer.id)).first()
    if existing is None:
        session.add(row)
    else:
        existing.puntuacion = row.puntuacion
        existing.pros = row.pros
        existing.contras = row.contras
        existing.recomendacion = row.recomendacion
        existing.razonamiento = row.razonamiento
    offer.estado = OfferEstado.evaluada
    if fit.recommendation == "skip":
        offer.razon_descarte = (fit.reasoning or "")[:200]
    session.flush()


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
        use_graph = get_settings().use_langgraph_eval

        fecha_inicio = _now()
        errors: list[dict[str, Any]] = []
        scraped = 0
        filtered = 0
        discarded = 0
        researched = 0
        evaluated = 0
        draft_count: list[int] = [0]
        manual_count: list[int] = [0]
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
                    discarded = sum(1 for o in nueva if o.estado == OfferEstado.descartada)
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
                    researched = sum(1 for o in filtrada if o.estado == OfferEstado.investigada)
                    log.info(
                        "stage_done",
                        stage="research",
                        username=username,
                        count=len(unique_names),
                    )

                # --- Stage 4: Evaluate (+ draft, when the LangGraph path is on) ---
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

                    if use_graph:
                        # LangGraph path: assess + draft per offer in one subgraph,
                        # superseding both the v1 evaluate and write stages.
                        evaluated, shipped, manual = await self._eval_draft_graph(
                            session, profile, investig, client, errors
                        )
                        draft_count[0] += shipped + manual
                        manual_count[0] += manual
                        log.info(
                            "stage_done",
                            stage="evaluate_and_draft_graph",
                            username=username,
                            count=evaluated,
                        )
                    else:
                        eval_agent = ViabilityEvaluator(client, session)

                        async def _do_eval(offer: Offer) -> None:
                            co_row = session.get(Company, offer.company_id)
                            if co_row is None:
                                return
                            await eval_agent.evaluate(offer, co_row, profile)

                        await run_per_offer(
                            "evaluate", investig, _do_eval, errors, self._concurrency
                        )
                        evaluated = sum(1 for o in investig if o.estado == OfferEstado.evaluada)
                        log.info("stage_done", stage="evaluate", username=username)

                # --- Stage 5: Write drafts (v1 path only; graph path drafts above) ---
                if not use_graph and "write" not in self._skip:
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
                        if draft.needs_manual_context:
                            manual_count[0] += 1

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
            ofertas_descartadas=discarded,
            ofertas_investigadas=researched,
            ofertas_evaluadas=evaluated,
            drafts_manual_context=manual_count[0],
            errores=errors,
            tokens_consumidos=tracker.summary(),
            coste_estimado_eur=tracker.total_cost_eur(),
            success=fatal is None,
            fatal_error=fatal,
        )

    async def _eval_draft_graph(
        self,
        session: Session,
        profile: UserProfile,
        candidates: list[Offer],
        client: AzureOpenAIClient,
        errors: list[dict[str, Any]],
    ) -> tuple[int, int, int]:
        """Run the ``evaluate_and_draft`` subgraph per offer (autonomous mode).

        Replaces the v1 evaluate + write stages when ``use_langgraph_eval`` is on.
        The human-review ``interrupt()`` is auto-resumed by mirroring the model's
        own verdict, so a draft is produced unattended for dashboard review (the
        HITL checkpoint stays at draft review, exactly as v1). Offers are processed
        sequentially because they share the orchestrator's session. Per-offer errors
        are isolated (offer -> ``error`` state) like :func:`run_per_offer`.

        Args:
            session: The orchestrator's active session (shared with graph nodes).
            profile: The user profile being processed.
            candidates: Researched offers to evaluate + draft.
            client: Azure OpenAI client (token-tracked).
            errors: Mutable error list; per-offer failures are appended.

        Returns:
            ``(evaluated, drafts_shipped, drafts_manual_context)``.
        """
        from langgraph.types import Command

        from src.graph.build import build_graph, open_checkpointer, thread_config

        username = profile.username

        @contextmanager
        def _shared() -> Iterator[Session]:
            # Graph nodes reuse the orchestrator's session so they see uncommitted
            # state (research cache hits) and never open a second SQLite writer.
            yield session

        evaluated = 0
        shipped = 0
        manual = 0

        async with open_checkpointer() as saver:
            # Treat the compiled graph as Any: langgraph's precise ainvoke/aget_state
            # overloads (RunnableConfig, Command generics) fight a plain dict config.
            graph: Any = build_graph(saver, client=client, session_factory=_shared)
            for offer in candidates:
                try:
                    cfg = thread_config(username, offer.id)
                    result = await graph.ainvoke(
                        {"offer_id": offer.id, "username": username}, config=cfg
                    )
                    if "__interrupt__" in result:
                        pre: FitAssessment = (await graph.aget_state(cfg)).values["fit"]
                        await graph.ainvoke(
                            Command(
                                resume={
                                    "decision": pre.recommendation,
                                    "lead_angle": None,
                                    "clarifications": {},
                                }
                            ),
                            config=cfg,
                        )
                    vals = (await graph.aget_state(cfg)).values
                    fit: FitAssessment = vals["fit"]
                    _upsert_evaluation(session, offer, fit)
                    evaluated += 1
                    if fit.recommendation == "skip":
                        continue
                    draft: CoverLetterDraft | None = vals.get("draft")
                    nmc = bool(vals.get("needs_manual_context", False))
                    draft_persistence.save_graph_draft(
                        draft,
                        offer=offer,
                        user=profile,
                        needs_manual_context=nmc,
                        db_session=session,
                    )
                    if nmc or draft is None:
                        manual += 1
                    else:
                        shipped += 1
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as exc:
                    offer.estado = OfferEstado.error
                    offer.error_note = f"{type(exc).__name__}: {str(exc)[:200]}"
                    errors.append(
                        {
                            "stage": "evaluate_and_draft_graph",
                            "offer_hash": offer.hash_unico,
                            "error_class": type(exc).__name__,
                            "message": str(exc)[:200],
                        }
                    )
                    log.warning(
                        "graph_stage_error",
                        offer_id=offer.id,
                        error_class=type(exc).__name__,
                    )
        return evaluated, shipped, manual

    async def run_for_all_users(self) -> list[RunResult]:
        """Run the pipeline sequentially for every user, then post a Telegram summary.

        Returns:
            One ``RunResult`` per user, in alphabetical username order.
        """
        results: list[RunResult] = []
        for username in self._discover_usernames():
            result = await self.run_for_user(username)
            results.append(result)

        if results:
            await telegram.send_message(format_summary(results))
            alert = format_cost_alert(results, _cost_alert_threshold())
            if alert is not None:
                await telegram.send_message(alert)
        return results


def _total_tokens(result: RunResult) -> int:
    """Sum total_tokens across all deployments in a run's usage summary."""
    return sum(
        int(v.get("total_tokens", 0))
        for v in result.tokens_consumidos.values()
        if isinstance(v, dict)
    )


def format_summary(results: list[RunResult]) -> str:
    """Render a MarkdownV2-safe Telegram summary of one workflow run.

    Global totals appear first, followed by a per-user breakdown (scrapeados,
    relevantes vs descartados, investigados, evaluados, drafts incl.
    ``needs_manual_context``, tokens, and estimated cost in EUR).

    Args:
        results: One ``RunResult`` per user from this run.

    Returns:
        A MarkdownV2-escaped message body ready for :func:`telegram.send_message`.
    """
    e = escape_markdown_v2

    g_scraped = sum(r.ofertas_scrapeadas for r in results)
    g_relevant = sum(r.ofertas_filtradas for r in results)
    g_discarded = sum(r.ofertas_descartadas for r in results)
    g_researched = sum(r.ofertas_investigadas for r in results)
    g_evaluated = sum(r.ofertas_evaluadas for r in results)
    g_drafts = sum(r.drafts_generados for r in results)
    g_manual = sum(r.drafts_manual_context for r in results)
    g_tokens = sum(_total_tokens(r) for r in results)
    g_cost = sum(r.coste_estimado_eur for r in results)

    lines: list[str] = [
        f"*{e('Resumen diario job-agent')}*",
        "",
        f"*{e('Totales')}*",
        e(f"Scrapeadas: {g_scraped} · Relevantes: {g_relevant} · Descartadas: {g_discarded}"),
        e(f"Investigadas: {g_researched} · Evaluadas: {g_evaluated}"),
        e(f"Drafts: {g_drafts} (manual: {g_manual})"),
        e(f"Tokens: {g_tokens} · Coste: {g_cost:.4f} EUR"),
    ]

    for r in results:
        status = "OK" if r.success else "FALLO"
        lines.append("")
        lines.append(f"*{e(r.username)}* {e(f'[{status}]')}")
        lines.append(
            e(
                f"Scrapeadas: {r.ofertas_scrapeadas} · Relevantes: {r.ofertas_filtradas} "
                f"· Descartadas: {r.ofertas_descartadas}"
            )
        )
        lines.append(
            e(f"Investigadas: {r.ofertas_investigadas} · Evaluadas: {r.ofertas_evaluadas}")
        )
        lines.append(e(f"Drafts: {r.drafts_generados} (manual: {r.drafts_manual_context})"))
        lines.append(e(f"Tokens: {_total_tokens(r)} · Coste: {r.coste_estimado_eur:.4f} EUR"))
        if r.errores:
            lines.append(e(f"Errores: {len(r.errores)}"))
        if r.fatal_error:
            lines.append(e(f"Fatal: {r.fatal_error}"))

    return "\n".join(lines)


def _cost_alert_threshold() -> float:
    """Return the per-run cost alert threshold, defaulting safely if config fails."""
    try:
        return get_settings().daily_cost_alert_eur
    except Exception:
        return 1.00


def format_cost_alert(results: list[RunResult], threshold: float) -> str | None:
    """Build a cost-alert message if this run breached the per-run threshold.

    The threshold is evaluated per run (not cumulative): an alert fires when the
    global total or any single user's estimated cost exceeds ``threshold``.

    Args:
        results: One ``RunResult`` per user from this run.
        threshold: Per-run cost ceiling in EUR.

    Returns:
        A MarkdownV2-escaped alert body, or ``None`` when no threshold is breached.
    """
    global_cost = sum(r.coste_estimado_eur for r in results)
    offenders = [r for r in results if r.coste_estimado_eur > threshold]

    if global_cost <= threshold and not offenders:
        return None

    e = escape_markdown_v2
    lines: list[str] = [
        f"*{e('⚠️ ALERTA DE COSTE')}*",
        "",
        e(f"Umbral por ejecución: {threshold:.2f} EUR"),
        e(f"Coste global de la ejecución: {global_cost:.4f} EUR"),
    ]

    if offenders:
        lines.append("")
        lines.append(f"*{e('Usuarios por encima del umbral')}*")
        for r in offenders:
            lines.append(
                e(
                    f"- {r.username}: {r.coste_estimado_eur:.4f} EUR "
                    f"({r.drafts_generados} drafts, manual {r.drafts_manual_context}, "
                    f"{_total_tokens(r)} tokens)"
                )
            )

    lines.append("")
    lines.append(
        e(
            "Posible causa: muchos drafts regenerados (revisa lint failures) "
            "o un volumen de ofertas inusual. Revisa run_logs."
        )
    )
    return "\n".join(lines)
