"""ApplicationWriter agent: generates application drafts using gpt-4o."""

from __future__ import annotations

import structlog

from src.db.models import Company, Offer
from src.exceptions import JobAgentError
from src.models.company import CompanyDossier
from src.models.draft import Draft
from src.models.evaluation import ViabilityEvaluation
from src.models.user_profile import UserProfile
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)


class ApplicationWriterError(JobAgentError):
    """Raised when the writer cannot produce a valid Draft."""


class ApplicationWriter:
    """Generate a tailored application ``Draft`` for an offer using gpt-4o.

    The user CV is rendered into the system message and marked cacheable, since
    it is stable across every offer processed for the same user within a run.
    This agent only generates and returns the ``Draft``; persisting it and the
    offer ``estado`` transition happen in Task 05.
    """

    def __init__(self, client: AzureOpenAIClient) -> None:
        self._client = client

    async def write(
        self,
        offer: Offer,
        company: Company,
        evaluation: ViabilityEvaluation,
        profile: UserProfile,
    ) -> Draft:
        """Generate an application draft for a single offer.

        Args:
            offer: SQLAlchemy ``Offer`` row, expected to have a recommendation
                of ``aplicar`` or ``dudar``.
            company: SQLAlchemy ``Company`` row with a populated ``dossier_json``.
            evaluation: The viability evaluation providing pros/cons context.
            profile: User profile providing the CV and target roles.

        Returns:
            A validated ``Draft`` (may be flagged ``needs_manual_context``).

        Raises:
            ApplicationWriterError: If the LLM returns an invalid response.
        """
        log = logger.bind(offer_id=offer.id, titulo=offer.titulo[:60])

        system = prompt_loader.load_system(
            "application_writer",
            cv_summary=profile.cv_for_prompt(),
        )
        user = prompt_loader.load_user(
            "application_writer",
            titulo=offer.titulo,
            empresa=offer.empresa,
            ubicacion=offer.ubicacion or "No especificada",
            modalidad=str(profile.location_preference.modality),
            descripcion=(offer.descripcion or "Sin descripción")[:4000],
            dossier_summary=self._build_dossier_summary(company),
            evaluation_ventajas=self._bullets(evaluation.ventajas),
            evaluation_desventajas=self._bullets(evaluation.desventajas),
            target_roles=", ".join(profile.target_roles),
        )

        result = await self._client.chat(
            deployment="4o",
            system=system,
            user=user,
            response_format=Draft,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, Draft):
            raise ApplicationWriterError(f"LLM did not return a valid Draft for offer {offer.id}")

        draft: Draft = result.parsed

        log.info(
            "application_draft_done",
            needs_manual_context=draft.needs_manual_context,
            flagged_reasons=draft.flagged_reasons,
            tokens=result.usage.total_tokens,
        )
        return draft

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
            logger.warning("application_writer_bad_dossier", company=company.nombre, error=str(exc))
            return f"Empresa: {company.nombre}. Dossier no disponible (error de formato)."

    @staticmethod
    def _bullets(items: list[str]) -> str:
        """Render a list of strings as a markdown bullet block, or a dash if empty."""
        if not items:
            return "- (ninguno)"
        return "\n".join(f"- {item}" for item in items)
