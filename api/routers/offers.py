"""Offers router: read-only per-user scraped-offer listing (any estado).

Surfaces every offer scraped for a user — including ones never analyzed
(`nueva`, `filtrada`) and discarded ones — independently of whether a draft was
produced. The drafts router only covers draft-backed offers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Exists, Select, func, select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import OfferCountsResponse, OfferListItem, OfferListResponse
from src.db.enums import OfferEstado
from src.db.models import Draft, Evaluation, Offer, User

router = APIRouter(prefix="/users", tags=["offers"])

DbSession = Annotated[Session, Depends(get_db)]

_VALID_ESTADOS: frozenset[str] = frozenset(e.value for e in OfferEstado)

# Review buckets derived from whether the offer has an evaluation row, NOT from
# estado. An offer killed by the cheap offer_filter (estado=descartada) never got
# an evaluation, so the user never reviewed it → "sin_analizar". Anything with an
# evaluation (evaluada / borrador_generado / enviada / post-eval descartada) was
# actually analyzed → "analizadas".
_VALID_BUCKETS: frozenset[str] = frozenset({"sin_analizar", "analizadas"})


def _eval_exists() -> Exists:
    """Correlated EXISTS over an offer's evaluation row."""
    return select(Evaluation.id).where(Evaluation.offer_id == Offer.id).exists()


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
    bucket: str | None = Query(default=None),
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
        bucket: Optional review bucket (``sin_analizar`` / ``analizadas``),
            derived from whether the offer has an evaluation row.
        plataforma: Optional source filter (matched against ``Offer.fuente``).
        q: Optional free-text filter over ``titulo`` / ``empresa``.
        page: 1-based page number.
        per_page: Page size (1-200).

    Raises:
        HTTPException: 404 if the user is unknown, 422 for an invalid ``estado``
            or ``bucket``.
    """
    user = _resolve_user(username, db)

    if estado is not None and estado not in _VALID_ESTADOS:
        raise HTTPException(status_code=422, detail=f"Invalid estado '{estado}'")
    if bucket is not None and bucket not in _VALID_BUCKETS:
        raise HTTPException(status_code=422, detail=f"Invalid bucket '{bucket}'")

    has_evaluation = _eval_exists().label("has_evaluation")
    has_draft = select(Draft.id).where(Draft.offer_id == Offer.id).exists().label("has_draft")
    latest_draft_id = (
        select(func.max(Draft.id))
        .where(Draft.offer_id == Offer.id)
        .scalar_subquery()
        .label("draft_id")
    )

    stmt: Select[tuple[Offer, bool, bool, int | None]] = (
        select(Offer, has_evaluation, has_draft, latest_draft_id)
        .where(Offer.user_id == user.id)
        .order_by(Offer.fecha_detectada.desc(), Offer.id.desc())
    )
    if estado is not None:
        stmt = stmt.where(Offer.estado == estado)
    if bucket == "sin_analizar":
        stmt = stmt.where(~_eval_exists())
    elif bucket == "analizadas":
        stmt = stmt.where(_eval_exists())
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
            draft_id=draft_id,
        )
        for offer, eval_flag, draft_flag, draft_id in rows
    ]

    return OfferListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/{username}/offers/counts", response_model=OfferCountsResponse)
def offer_counts(username: str, db: DbSession) -> OfferCountsResponse:
    """Return per-estado and per-review-bucket offer counts for *username*."""
    user = _resolve_user(username, db)

    rows = db.execute(
        select(Offer.estado, func.count()).where(Offer.user_id == user.id).group_by(Offer.estado)
    ).all()
    counts = {estado: int(count) for estado, count in rows}
    total = sum(counts.values())

    analizadas: int = db.execute(
        select(func.count()).select_from(Offer).where(Offer.user_id == user.id, _eval_exists())
    ).scalar_one()
    buckets = {"analizadas": analizadas, "sin_analizar": total - analizadas}

    return OfferCountsResponse(counts=counts, buckets=buckets, total=total)
