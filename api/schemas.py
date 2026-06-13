"""Pydantic response and request schemas for the dashboard API."""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel


class UserOut(BaseModel):
    """Minimal user representation."""

    id: int
    username: str
    nombre: str


# ---------------------------------------------------------------------------
# Drafts list
# ---------------------------------------------------------------------------


class DraftListItem(BaseModel):
    """Summary row for the drafts list view."""

    id: int
    estado: str
    asunto: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    offer_id: int
    offer_titulo: str
    offer_empresa: str
    offer_ubicacion: str | None
    offer_fuente: str
    offer_url: str | None
    offer_estado: str
    company_nombre: str | None
    company_sector: str | None
    puntuacion: int | None
    recomendacion: str | None


class DraftListResponse(BaseModel):
    """Paginated draft listing."""

    items: list[DraftListItem]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# Draft detail
# ---------------------------------------------------------------------------


class OfferOut(BaseModel):
    """Full offer fields for the detail view."""

    id: int
    titulo: str
    empresa: str
    ubicacion: str | None
    descripcion: str | None
    url: str | None
    fuente: str
    fecha_publicacion: datetime.datetime | None
    fecha_detectada: datetime.datetime
    estado: str


class CompanyOut(BaseModel):
    """Company record including raw dossier JSON."""

    id: int
    nombre: str
    website: str | None
    sector: str | None
    descripcion: str | None
    dossier_json: Any


class EvaluationOut(BaseModel):
    """Evaluation record for the detail view."""

    id: int
    puntuacion: int
    pros: Any
    contras: Any
    recomendacion: str
    razonamiento: str | None


class ApplicationOut(BaseModel):
    """Application submission record."""

    id: int
    metodo_envio: str
    fecha_envio: datetime.datetime
    notas: str | None
    tipo_respuesta: str | None
    fecha_respuesta: datetime.datetime | None


class DraftDetail(BaseModel):
    """Full draft detail joined with offer, company, evaluation, and application."""

    id: int
    estado: str
    asunto: str | None
    cuerpo_email: str | None
    carta_presentacion: str | None
    intento_num: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    offer: OfferOut
    company: CompanyOut | None
    evaluation: EvaluationOut | None
    application: ApplicationOut | None


# ---------------------------------------------------------------------------
# Action requests / responses
# ---------------------------------------------------------------------------


class DraftPatchRequest(BaseModel):
    """Body for PATCH /drafts/{id}. Only provided fields are updated."""

    asunto: str | None = None
    cuerpo_email: str | None = None
    carta_presentacion: str | None = None


class MarkSentRequest(BaseModel):
    """Body for POST /drafts/{id}/mark-sent."""

    method: str
    notes: str | None = None
    ps_text: str | None = None


class MarkSentResponse(BaseModel):
    """Response after marking a draft as sent."""

    application_id: int
    offer_estado: str


class RegenerateResponse(BaseModel):
    """Response after regenerating a draft."""

    draft_id: int
    estado: str
    asunto: str | None
    cuerpo_email: str | None
    carta_presentacion: str | None
    needs_manual_context: bool


# ---------------------------------------------------------------------------
# Offers list (all states, per user)
# ---------------------------------------------------------------------------


class OfferListItem(BaseModel):
    """Summary row for the scraped-offers list view (any estado)."""

    id: int
    titulo: str
    empresa: str
    ubicacion: str | None
    fuente: str
    url: str | None
    fecha_publicacion: datetime.datetime | None
    fecha_detectada: datetime.datetime
    estado: str
    razon_descarte: str | None
    has_draft: bool
    has_evaluation: bool


class OfferListResponse(BaseModel):
    """Paginated scraped-offers listing."""

    items: list[OfferListItem]
    total: int
    page: int
    per_page: int


class OfferCountsResponse(BaseModel):
    """Per-estado offer counts for a user (drives filter chips + badges)."""

    counts: dict[str, int]
    total: int


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


class HistoryItem(BaseModel):
    """Single application history row."""

    application_id: int
    offer_titulo: str
    offer_empresa: str
    offer_fuente: str
    draft_asunto: str | None
    metodo_envio: str
    fecha_envio: datetime.datetime
    tipo_respuesta: str | None
    fecha_respuesta: datetime.datetime | None
    notas: str | None


class HistoryResponse(BaseModel):
    """Paginated application history."""

    items: list[HistoryItem]
    total: int
    page: int
    per_page: int
