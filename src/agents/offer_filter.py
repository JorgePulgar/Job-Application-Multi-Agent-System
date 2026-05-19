"""OfferFilter agent: classifies scraped offers as relevant or discarded."""

from __future__ import annotations

import structlog

from src.db.enums import OfferEstado
from src.db.models import Offer
from src.exceptions import JobAgentError
from src.models.decisions import FilterBatchSummary, FilterDecision
from src.models.user_profile import UserProfile
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)


class OfferFilterError(JobAgentError):
    """Raised when the filter agent cannot produce a valid decision."""


class OfferFilter:
    """Classify offers as relevant or discarded using a cheap LLM (gpt-4o-mini).

    Pre-LLM red-flag short-circuit: if any ``profile.red_flags`` substring matches
    the offer title or description (case-insensitive), the offer is immediately
    discarded without spending an LLM token.

    The agent is intentionally sequential — no internal concurrency.  The
    orchestrator controls how many users run in parallel.
    """

    def __init__(self, client: AzureOpenAIClient) -> None:
        self._client = client
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = prompt_loader.load_system("offer_filter")
        return self._system_prompt

    def _check_red_flags(self, offer: Offer, profile: UserProfile) -> str | None:
        """Return the first matching red-flag substring, or None if no match."""
        haystack = (f"{offer.titulo} {offer.descripcion or ''}").lower()
        for flag in profile.red_flags:
            if flag.lower() in haystack:
                return flag
        return None

    async def evaluate(self, offer: Offer, profile: UserProfile) -> FilterDecision:
        """Classify a single offer and update its DB state in-place.

        The ``offer`` ORM object is mutated directly — the caller owns the
        session and is responsible for committing or rolling back.

        Args:
            offer: SQLAlchemy ``Offer`` row attached to an active session.
            profile: User profile providing filtering criteria.

        Returns:
            ``FilterDecision`` with ``relevant`` and optional ``razon_descarte``.

        Raises:
            OfferFilterError: If the LLM returns an unparseable response after
                the wrapper's retries are exhausted.
        """
        log = logger.bind(offer_id=offer.id, titulo=offer.titulo[:60])

        # --- Pre-LLM red-flag short-circuit ---
        matched_flag = self._check_red_flags(offer, profile)
        if matched_flag is not None:
            reason = f"Red flag detectada: «{matched_flag}»"[:200]
            decision = FilterDecision(relevant=False, razon_descarte=reason)
            offer.estado = OfferEstado.descartada
            offer.razon_descarte = reason
            log.info("offer_filter_red_flag", flag=matched_flag)
            return decision

        # --- LLM call ---
        system = self._get_system_prompt()
        user = prompt_loader.load_user(
            "offer_filter",
            titulo=offer.titulo,
            empresa=offer.empresa,
            ubicacion=offer.ubicacion or "No especificada",
            modalidad=offer.fuente,  # fuente holds platform; modalidad comes from raw_json
            descripcion=(offer.descripcion or "Sin descripción")[:4000],
            target_roles=", ".join(profile.target_roles),
            target_sectors=(
                ", ".join(profile.target_sectors) if profile.target_sectors else "No especificados"
            ),
            red_flags=", ".join(profile.red_flags) if profile.red_flags else "Ninguno",
            location_preference=str(profile.location_preference.modality),
        )

        result = await self._client.chat(
            deployment="mini",
            system=system,
            user=user,
            response_format=FilterDecision,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, FilterDecision):
            raise OfferFilterError(
                f"LLM did not return a valid FilterDecision for offer {offer.id}"
            )

        decision = result.parsed

        # Truncate razon_descarte defensively in case the model exceeded the limit
        if decision.razon_descarte is not None:
            decision = FilterDecision(
                relevant=decision.relevant,
                razon_descarte=decision.razon_descarte[:200],
            )

        # --- Update DB state ---
        if decision.relevant:
            offer.estado = OfferEstado.filtrada
            offer.razon_descarte = None
        else:
            offer.estado = OfferEstado.descartada
            offer.razon_descarte = decision.razon_descarte

        log.info(
            "offer_filter_decision",
            relevant=decision.relevant,
            tokens=result.usage.total_tokens,
        )
        return decision

    async def evaluate_batch(
        self,
        offers: list[Offer],
        profile: UserProfile,
    ) -> FilterBatchSummary:
        """Evaluate a list of offers sequentially and return aggregated stats.

        Args:
            offers: List of Offer ORM objects attached to an active session.
            profile: User profile providing filtering criteria.

        Returns:
            ``FilterBatchSummary`` with all decisions and token usage totals.
        """
        summary = FilterBatchSummary()

        for offer in offers:
            was_red_flag = self._check_red_flags(offer, profile) is not None

            decision = await self.evaluate(offer, profile)
            summary.decisions.append(decision)

            if decision.relevant:
                summary.relevant_count += 1
            else:
                summary.discarded_count += 1
                if was_red_flag:
                    summary.red_flag_count += 1

        return summary
