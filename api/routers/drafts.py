"""Drafts router: detail, mark-sent, discard, regenerate."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db, get_profiles_dir
from api.schemas import (
    ApplicationOut,
    CompanyOut,
    DraftDetail,
    EvaluationOut,
    MarkSentRequest,
    MarkSentResponse,
    OfferOut,
    RegenerateResponse,
)
from src.db.enums import DraftEstado, OfferEstado
from src.db.models import Application, Company, Draft, Evaluation, Offer

router = APIRouter(prefix="/drafts", tags=["drafts"])

DbSession = Annotated[Session, Depends(get_db)]
ProfilesDir = Annotated[Path, Depends(get_profiles_dir)]


def _get_draft_or_404(draft_id: int, db: Session) -> Draft:
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


def _offer_out(offer: Offer) -> OfferOut:
    return OfferOut(
        id=offer.id,
        titulo=offer.titulo,
        empresa=offer.empresa,
        ubicacion=offer.ubicacion,
        descripcion=offer.descripcion,
        url=offer.url,
        fuente=offer.fuente,
        fecha_publicacion=offer.fecha_publicacion,
        fecha_detectada=offer.fecha_detectada,
        estado=offer.estado,
    )


def _company_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        nombre=company.nombre,
        website=company.website,
        sector=company.sector,
        descripcion=company.descripcion,
        dossier_json=company.dossier_json,
    )


def _eval_out(ev: Evaluation) -> EvaluationOut:
    return EvaluationOut(
        id=ev.id,
        puntuacion=ev.puntuacion,
        pros=ev.pros,
        contras=ev.contras,
        recomendacion=ev.recomendacion,
        razonamiento=ev.razonamiento,
    )


def _app_out(app: Application) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        metodo_envio=app.metodo_envio,
        fecha_envio=app.fecha_envio,
        notas=app.notas,
        tipo_respuesta=app.tipo_respuesta,
        fecha_respuesta=app.fecha_respuesta,
    )


@router.get("/{draft_id}", response_model=DraftDetail)
def get_draft(draft_id: int, db: DbSession) -> DraftDetail:
    """Return full draft detail joined with offer, company, evaluation, application."""
    draft = _get_draft_or_404(draft_id, db)
    offer: Offer = draft.offer
    company: Company | None = offer.company
    evaluation: Evaluation | None = offer.evaluation
    application: Application | None = draft.application

    return DraftDetail(
        id=draft.id,
        estado=draft.estado,
        asunto=draft.asunto,
        cuerpo_email=draft.cuerpo_email,
        carta_presentacion=draft.carta_presentacion,
        intento_num=draft.intento_num,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        offer=_offer_out(offer),
        company=_company_out(company) if company else None,
        evaluation=_eval_out(evaluation) if evaluation else None,
        application=_app_out(application) if application else None,
    )


@router.post("/{draft_id}/mark-sent", response_model=MarkSentResponse, status_code=201)
def mark_sent(draft_id: int, body: MarkSentRequest, db: DbSession) -> MarkSentResponse:
    """Record a sent application: create Application row, update offer estado."""
    draft = _get_draft_or_404(draft_id, db)

    if draft.application is not None:
        raise HTTPException(status_code=409, detail="Draft already marked as sent")

    combined_notes: str | None = body.notes
    if body.ps_text:
        ps_line = f"P.S.: {body.ps_text}"
        combined_notes = f"{body.notes}\n\n{ps_line}" if body.notes else ps_line

    app = Application(
        draft_id=draft.id,
        offer_id=draft.offer_id,
        user_id=draft.user_id,
        metodo_envio=body.method,
        fecha_envio=datetime.datetime.now(datetime.UTC),
        notas=combined_notes,
    )
    db.add(app)

    offer: Offer = draft.offer
    offer.estado = OfferEstado.enviada
    db.flush()

    return MarkSentResponse(application_id=app.id, offer_estado=offer.estado)


@router.post("/{draft_id}/discard")
def discard_draft(draft_id: int, db: DbSession) -> dict[str, str]:
    """Discard a draft: set offer estado to descartada."""
    draft = _get_draft_or_404(draft_id, db)
    offer: Offer = draft.offer
    offer.estado = OfferEstado.descartada
    offer.razon_descarte = "manual_review"
    draft.estado = DraftEstado.rechazado
    db.flush()
    return {"offer_estado": offer.estado}


@router.post("/{draft_id}/regenerate", response_model=RegenerateResponse)
async def regenerate_draft(
    draft_id: int,
    db: DbSession,
    profiles_dir: ProfilesDir,
) -> RegenerateResponse:
    """Regenerate the draft by calling ApplicationWriter inline."""
    draft = _get_draft_or_404(draft_id, db)
    offer: Offer = draft.offer
    company: Company | None = offer.company
    evaluation: Evaluation | None = offer.evaluation

    if evaluation is None:
        raise HTTPException(status_code=422, detail="Offer has no evaluation — cannot regenerate")

    # Load user profile from YAML
    profile_path = profiles_dir / f"{draft.user.username}.yaml"
    if not profile_path.exists():
        raise HTTPException(
            status_code=422, detail=f"Profile YAML not found for '{draft.user.username}'"
        )
    with profile_path.open(encoding="utf-8") as fh:
        profile_data: dict[str, Any] = yaml.safe_load(fh)

    from src.models.evaluation import ViabilityEvaluation
    from src.models.user_profile import UserProfile

    try:
        profile = UserProfile.model_validate(profile_data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid profile YAML: {exc}") from exc

    try:
        eval_model = ViabilityEvaluation(
            score=evaluation.puntuacion,
            ventajas=evaluation.pros or [],
            desventajas=(evaluation.contras or {}).get("desventajas", []),
            red_flags_match=(evaluation.contras or {}).get("red_flags_match", []),
            recomendacion=cast(Literal["aplicar", "dudar", "descartar"], evaluation.recomendacion),
            reasoning=evaluation.razonamiento or "",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Cannot reconstruct evaluation model: {exc}"
        ) from exc

    from src.agents.application_writer import ApplicationWriter
    from src.services.azure_openai import AzureOpenAIClient

    client = AzureOpenAIClient()
    writer = ApplicationWriter(client)
    new_draft = await writer.write(
        offer=offer,
        company=company if company is not None else _stub_company(offer),
        evaluation=eval_model,
        profile=profile,
    )

    draft.asunto = new_draft.email_subject or None
    draft.cuerpo_email = new_draft.email_body or None
    draft.carta_presentacion = new_draft.carta_presentacion
    if new_draft.needs_manual_context:
        draft.estado = DraftEstado.needs_manual_context
    else:
        draft.estado = DraftEstado.pendiente
    draft.intento_num += 1
    db.flush()

    return RegenerateResponse(
        draft_id=draft.id,
        estado=draft.estado,
        asunto=draft.asunto,
        cuerpo_email=draft.cuerpo_email,
        carta_presentacion=draft.carta_presentacion,
        needs_manual_context=new_draft.needs_manual_context,
    )


def _stub_company(offer: Offer) -> Any:
    """Return a minimal Company-like object when no company row exists."""
    from src.db.models import Company as CompanyModel

    stub = CompanyModel.__new__(CompanyModel)
    stub.id = 0
    stub.nombre = offer.empresa
    stub.website = None
    stub.sector = None
    stub.descripcion = None
    stub.dossier_json = None
    stub.fecha_research = None
    stub.expira_en = None
    return stub
