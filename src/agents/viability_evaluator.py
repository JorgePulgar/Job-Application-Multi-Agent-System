"""ViabilityEvaluator agent: scores job offers using gpt-4o."""

from __future__ import annotations

import structlog
from sqlalchemy.orm import Session

from src.db.enums import OfferEstado
from src.db.models import Company, Evaluation, Offer
from src.exceptions import JobAgentError
from src.models.company import CompanyDossier
from src.models.evaluation import ViabilityEvaluation
from src.models.user_profile import UserProfile
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)


class ViabilityEvaluatorError(JobAgentError):
    """Raised when the evaluator cannot produce a valid ViabilityEvaluation."""


class ViabilityEvaluator:
    """Score a filtered offer's viability for a given user profile using gpt-4o.

    The session is owned by the caller; this agent only adds rows, never commits.
    """

    def __init__(self, client: AzureOpenAIClient, session: Session) -> None:
        self._client = client
        self._session = session
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = prompt_loader.load_system("viability_evaluator")
        return self._system_prompt

    async def evaluate(
        self,
        offer: Offer,
        company: Company,
        profile: UserProfile,
    ) -> ViabilityEvaluation:
        """Score an offer and persist the result to the evaluations table.

        Mutates ``offer.estado`` to ``evaluada``.  The caller owns the session
        and must commit or roll back.

        Args:
            offer: SQLAlchemy ``Offer`` row attached to an active session.
            company: SQLAlchemy ``Company`` row with a populated ``dossier_json``.
            profile: User profile providing scoring criteria.

        Returns:
            Validated ``ViabilityEvaluation`` with score and recommendation.

        Raises:
            ViabilityEvaluatorError: If the LLM returns an invalid response.
        """
        log = logger.bind(offer_id=offer.id, titulo=offer.titulo[:60])

        dossier_summary = self._build_dossier_summary(company)

        system = self._get_system_prompt()
        user = prompt_loader.load_user(
            "viability_evaluator",
            titulo=offer.titulo,
            empresa=offer.empresa,
            ubicacion=offer.ubicacion or "No especificada",
            descripcion=(offer.descripcion or "Sin descripción")[:4000],
            salario=self._salary_text(offer),
            dossier=dossier_summary,
            target_roles=", ".join(profile.target_roles),
            target_sectors=(
                ", ".join(profile.target_sectors) if profile.target_sectors else "No especificados"
            ),
            tech_stack=", ".join(profile.tech_stack) if profile.tech_stack else "No especificado",
            red_flags=", ".join(profile.red_flags) if profile.red_flags else "Ninguno",
            salario_minimo=(
                f"{profile.min_salary:,} €/año" if profile.min_salary else "No especificado"
            ),
            modalidad=str(profile.location_preference.modality),
        )

        result = await self._client.chat(
            deployment="4o",
            system=system,
            user=user,
            response_format=ViabilityEvaluation,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, ViabilityEvaluation):
            raise ViabilityEvaluatorError(
                f"LLM did not return a valid ViabilityEvaluation for offer {offer.id}"
            )

        evaluation: ViabilityEvaluation = result.parsed

        self._persist(offer, evaluation)

        log.info(
            "viability_evaluation_done",
            score=evaluation.score,
            recomendacion=evaluation.recomendacion,
            tokens=result.usage.total_tokens,
        )
        return evaluation

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_dossier_summary(self, company: Company) -> str:
        """Return a prompt-ready company summary from the stored dossier JSON."""
        if company.dossier_json is None:
            return f"Empresa: {company.nombre}. Sin dossier disponible."
        try:
            dossier = CompanyDossier.model_validate(company.dossier_json)
            return dossier.to_summary_for_prompt()
        except Exception as exc:
            logger.warning(
                "viability_evaluator_bad_dossier", company=company.nombre, error=str(exc)
            )
            return f"Empresa: {company.nombre}. Dossier no disponible (error de formato)."

    @staticmethod
    def _salary_text(offer: Offer) -> str:
        """Extract salary info from raw_json, or return a fallback string."""
        if isinstance(offer.raw_json, dict):
            salary = offer.raw_json.get("salary_min") or offer.raw_json.get("salario")
            if salary:
                return str(salary)
        return "No especificado"

    def _persist(self, offer: Offer, evaluation: ViabilityEvaluation) -> None:
        """Write the Evaluation row and update offer estado."""
        db_row: Evaluation = evaluation.to_db_row(offer_id=offer.id)
        self._session.add(db_row)
        offer.estado = OfferEstado.evaluada
        self._session.flush()
