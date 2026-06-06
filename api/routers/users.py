"""Users router: list users and their draft listings."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import DraftListItem, DraftListResponse, UserOut
from src.db.models import Company, Draft, Evaluation, Offer, User

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]

# Map the "draft_ready" alias (used by the dashboard) to its real DB value.
_STATE_ALIAS: dict[str, str] = {"draft_ready": "pendiente"}


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession) -> list[UserOut]:
    """Return all registered users."""
    rows = db.execute(select(User).order_by(User.username)).scalars().all()
    return [UserOut(id=u.id, username=u.username, nombre=u.nombre) for u in rows]


@router.get("/{username}/drafts", response_model=DraftListResponse)
def list_drafts(
    username: str,
    db: DbSession,
    state: str | None = Query(default=None),
    sort: str = Query(default="created_at"),
    platform: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    recomendacion: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> DraftListResponse:
    """Return paginated drafts for a user, joined with offer/company/evaluation."""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    real_state = _STATE_ALIAS.get(state or "", state) if state else None

    stmt = (
        select(Draft, Offer, Company, Evaluation)
        .join(Offer, Draft.offer_id == Offer.id)
        .outerjoin(Company, Offer.company_id == Company.id)
        .outerjoin(Evaluation, Evaluation.offer_id == Offer.id)
        .where(Draft.user_id == user.id)
    )

    if real_state is not None:
        stmt = stmt.where(Draft.estado == real_state)
    if platform is not None:
        stmt = stmt.where(Offer.fuente == platform)
    if sector is not None:
        stmt = stmt.where(Company.sector == sector)
    if recomendacion is not None:
        stmt = stmt.where(Evaluation.recomendacion == recomendacion)

    if sort == "score":
        stmt = stmt.order_by(Evaluation.puntuacion.desc().nulls_last())
    elif sort == "company":
        stmt = stmt.order_by(func.coalesce(Company.nombre, Offer.empresa).asc())
    else:
        stmt = stmt.order_by(Draft.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = [
        DraftListItem(
            id=draft.id,
            estado=draft.estado,
            asunto=draft.asunto,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            offer_id=offer.id,
            offer_titulo=offer.titulo,
            offer_empresa=offer.empresa,
            offer_ubicacion=offer.ubicacion,
            offer_fuente=offer.fuente,
            offer_url=offer.url,
            offer_estado=offer.estado,
            company_nombre=company.nombre if company else None,
            company_sector=company.sector if company else None,
            puntuacion=evaluation.puntuacion if evaluation else None,
            recomendacion=evaluation.recomendacion if evaluation else None,
        )
        for draft, offer, company, evaluation in rows
    ]

    return DraftListResponse(items=items, total=total, page=page, per_page=per_page)
