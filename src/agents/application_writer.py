"""ApplicationWriter agent: generates application drafts using gpt-4o."""

from __future__ import annotations

import structlog

from src.db.models import Company, Offer
from src.exceptions import JobAgentError
from src.models.company import CompanyDossier
from src.models.draft import Draft
from src.models.evaluation import ViabilityEvaluation
from src.models.user_profile import UserProfile
from src.services import draft_lint, prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)

# Maximum regeneration attempts after the first generation fails the lint.
_MAX_RETRIES = 2


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
            A validated ``Draft``. May be flagged ``needs_manual_context`` if
            the model self-flags or the draft still fails the lint after
            ``_MAX_RETRIES`` regenerations.

        Raises:
            ApplicationWriterError: If the LLM returns an invalid response.
        """
        log = logger.bind(offer_id=offer.id, titulo=offer.titulo[:60])

        dossier = self._parse_dossier(company)
        system = prompt_loader.load_system(
            "application_writer",
            cv_summary=profile.cv_for_prompt(),
        )
        base_user = prompt_loader.load_user(
            "application_writer",
            titulo=offer.titulo,
            empresa=offer.empresa,
            ubicacion=offer.ubicacion or "No especificada",
            modalidad=str(profile.location_preference.modality),
            descripcion=(offer.descripcion or "Sin descripción")[:4000],
            dossier_summary=self._dossier_summary(dossier, company.nombre),
            evaluation_ventajas=self._bullets(evaluation.ventajas),
            evaluation_desventajas=self._bullets(evaluation.desventajas),
            target_roles=", ".join(profile.target_roles),
        )

        last_draft: Draft | None = None
        last_issues: list[str] = []

        for attempt in range(_MAX_RETRIES + 1):
            user = base_user if attempt == 0 else f"{base_user}\n\n{self._feedback(last_issues)}"

            result = await self._client.chat(
                deployment="4o",
                system=system,
                user=user,
                response_format=Draft,
                cacheable_system=True,
            )
            if result.parsed is None or not isinstance(result.parsed, Draft):
                raise ApplicationWriterError(
                    f"LLM did not return a valid Draft for offer {offer.id}"
                )

            draft = result.parsed
            if draft.needs_manual_context:
                log.info("application_draft_model_flagged", attempt=attempt)
                return draft

            last_draft = draft
            lint_result = draft_lint.lint(draft, dossier, company.nombre)
            if lint_result.ok:
                log.info(
                    "application_draft_done",
                    attempt=attempt,
                    tokens=result.usage.total_tokens,
                )
                return self._append_signature(draft, profile)

            last_issues = lint_result.issues
            log.info("application_draft_lint_failed", attempt=attempt, issues=last_issues)

        log.warning("application_draft_flagged_after_retries", issues=last_issues)
        return self._flagged_draft(last_draft, last_issues)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_dossier(self, company: Company) -> CompanyDossier | None:
        """Parse the stored dossier JSON into a CompanyDossier, or None on failure."""
        if company.dossier_json is None:
            return None
        try:
            return CompanyDossier.model_validate(company.dossier_json)
        except Exception as exc:
            logger.warning("application_writer_bad_dossier", company=company.nombre, error=str(exc))
            return None

    @staticmethod
    def _dossier_summary(dossier: CompanyDossier | None, nombre: str) -> str:
        """Return a prompt-ready company summary, or a fallback when unavailable."""
        if dossier is None:
            return f"Empresa: {nombre}. Sin dossier disponible (o con error de formato)."
        return dossier.to_summary_for_prompt()

    @staticmethod
    def _feedback(issues: list[str]) -> str:
        """Render lint issues as a corrective instruction block for regeneration."""
        bullets = "\n".join(f"- {issue}" for issue in issues)
        return (
            "## Corrige estos problemas del borrador anterior\n"
            "El borrador anterior fue rechazado por estos motivos. Corrígelos todos:\n"
            f"{bullets}"
        )

    @staticmethod
    def _flagged_draft(last_draft: Draft | None, issues: list[str]) -> Draft:
        """Build a needs_manual_context Draft after retries are exhausted.

        ``Draft`` requires 3-5 ``experiencias_destacadas`` even when flagged, so
        the last attempt's experiences are reused when available.
        """
        experiencias = (
            last_draft.experiencias_destacadas
            if last_draft is not None
            else ["(pendiente)", "(pendiente)", "(pendiente)"]
        )
        return Draft(
            email_subject="",
            email_body="",
            carta_presentacion=None,
            experiencias_destacadas=experiencias,
            needs_manual_context=True,
            flagged_reasons=issues,
        )

    @staticmethod
    def _bullets(items: list[str]) -> str:
        """Render a list of strings as a markdown bullet block, or a dash if empty."""
        if not items:
            return "- (ninguno)"
        return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def _append_signature(draft: Draft, profile: UserProfile) -> Draft:
        """Append the user's deterministic HTML signature to a complete draft.

        Flagged drafts (``needs_manual_context``) have an empty body and are
        left untouched. The signature is built from profile data, not generated
        by the model, so the HTML is never mangled.

        Args:
            draft: The model-generated draft.
            profile: User profile providing the signature.

        Returns:
            A copy of *draft* with the signature appended to ``email_body``,
            or the original draft if it is flagged.
        """
        if draft.needs_manual_context:
            return draft
        body = f"{draft.email_body}\n\n{profile.signature_html()}"
        return draft.model_copy(update={"email_body": body})
