"""Offers router: read-only per-user scraped-offer listing (any estado).

Surfaces every offer scraped for a user — including ones never analyzed
(`nueva`, `filtrada`) and discarded ones — independently of whether a draft was
produced. The drafts router only covers draft-backed offers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import OfferCountsResponse, OfferListItem, OfferListResponse
from src.db.enums import OfferEstado
from src.db.models import Draft, Evaluation, Offer, User

router = APIRouter(prefix="/users", tags=["offers"])

DbSession = Annotated[Session, Depends(get_db)]

_VALID_ESTADOS: frozenset[str] = frozenset(e.value for e in OfferEstado)


def _resolve_user(username: str, db: Session) -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{username}/offers", response_model=OfferListResponse)
def list_offers(
    username: str,
    db: DbSession,
    estado: str | None = Query(default=None),
    plataforma: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
) -> OfferListResponse:
    """Return paginated scraped offers for *username*, newest first.

    Args:
        username: Owner of the offers.
        db: Injected DB session.
        estado: Optional ``OfferEstado`` filter; ``None`` returns all states.
        plataforma: Optional source filter (matched against ``Offer.fuente``).
        q: Optional free-text filter over ``titulo`` / ``empresa``.
        page: 1-based page number.
        per_page: Page size (1-200).

    Raises:
        HTTPException: 404 if the user is unknown, 422 for an invalid ``estado``.
    """
    user = _resolve_user(username, db)

    if estado is not None and estado not in _VALID_ESTADOS:
        raise HTTPException(status_code=422, detail=f"Invalid estado '{estado}'")

    has_evaluation = (
        select(Evaluation.id)
        .where(Evaluation.offer_id == Offer.id)
        .exists()
        .label("has_evaluation")
    )
    has_draft = select(Draft.id).where(Draft.offer_id == Offer.id).exists().label("has_draft")

    stmt: Select[tuple[Offer, bool, bool]] = (
        select(Offer, has_evaluation, has_draft)
        .where(Offer.user_id == user.id)
        .order_by(Offer.fecha_detectada.desc(), Offer.id.desc())
    )
    if estado is not None:
        stmt = stmt.where(Offer.estado == estado)
    if plataforma is not None:
        stmt = stmt.where(Offer.fuente == plataforma)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Offer.titulo.ilike(like) | Offer.empresa.ilike(like))

    total: int = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = [
        OfferListItem(
            id=offer.id,
            titulo=offer.titulo,
            empresa=offer.empresa,
            ubicacion=offer.ubicacion,
            fuente=offer.fuente,
            url=offer.url,
            fecha_publicacion=offer.fecha_publicacion,
            fecha_detectada=offer.fecha_detectada,
            estado=offer.estado,
            razon_descarte=offer.razon_descarte,
            has_draft=bool(draft_flag),
            has_evaluation=bool(eval_flag),
        )
        for offer, eval_flag, draft_flag in rows
    ]

    return OfferListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/{username}/offers/counts", response_model=OfferCountsResponse)
def offer_counts(username: str, db: DbSession) -> OfferCountsResponse:
    """Return a per-estado offer count map for *username* (one grouped query)."""
    user = _resolve_user(username, db)

    rows = db.execute(
        select(Offer.estado, func.count()).where(Offer.user_id == user.id).group_by(Offer.estado)
    ).all()

    counts = {estado: int(count) for estado, count in rows}
    return OfferCountsResponse(counts=counts, total=sum(counts.values()))
