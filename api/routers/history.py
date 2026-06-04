"""History router: application history per user."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import HistoryItem, HistoryResponse
from src.db.models import Application, Draft, Offer, User

router = APIRouter(prefix="/users", tags=["history"])

DbSession = Annotated[Session, Depends(get_db)]

# Map dashboard state labels to tipo_respuesta DB values.
_STATE_TO_TIPO: dict[str, str | None] = {
    "applied": None,  # handled separately as IS NULL / sin_respuesta
    "rejected": "negativa",
    "interview": "en_proceso",
    "hired": "positiva",
}


@router.get("/{username}/history", response_model=HistoryResponse)
def list_history(
    username: str,
    db: DbSession,
    state: str | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None, alias="from"),
    to_date: datetime.date | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> HistoryResponse:
    """Return paginated application history for a user."""
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = (
        select(Application, Offer, Draft)
        .join(Offer, Application.offer_id == Offer.id)
        .join(Draft, Application.draft_id == Draft.id)
        .where(Application.user_id == user.id)
    )

    if state is not None:
        if state == "applied":
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(
                    Application.tipo_respuesta.is_(None),
                    Application.tipo_respuesta == "sin_respuesta",
                )
            )
        elif state in _STATE_TO_TIPO:
            tipo = _STATE_TO_TIPO[state]
            if tipo is not None:
                stmt = stmt.where(Application.tipo_respuesta == tipo)

    if from_date is not None:
        stmt = stmt.where(Application.fecha_envio >= from_date)
    if to_date is not None:
        stmt = stmt.where(Application.fecha_envio <= to_date)

    stmt = stmt.order_by(Application.fecha_envio.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = [
        HistoryItem(
            application_id=app.id,
            offer_titulo=offer.titulo,
            offer_empresa=offer.empresa,
            offer_fuente=offer.fuente,
            draft_asunto=draft.asunto,
            metodo_envio=app.metodo_envio,
            fecha_envio=app.fecha_envio,
            tipo_respuesta=app.tipo_respuesta,
            fecha_respuesta=app.fecha_respuesta,
            notas=app.notas,
        )
        for app, offer, draft in rows
    ]

    return HistoryResponse(items=items, total=total, page=page, per_page=per_page)
