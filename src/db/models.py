"""SQLAlchemy ORM models for the v1 job-agent database schema."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.db.enums import (
    DraftEstado,
    MetodoEnvio,
    OfferEstado,
    Recomendacion,
    RunEstado,
    TipoRespuesta,
)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class User(Base):
    """Registered user of the system (one row per profile YAML)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    offers: Mapped[list[Offer]] = relationship("Offer", back_populates="user")
    drafts: Mapped[list[Draft]] = relationship("Draft", back_populates="user")
    run_logs: Mapped[list[RunLog]] = relationship("RunLog", back_populates="user")


class Company(Base):
    """Company researched during the pipeline."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(256), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    dossier_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    fecha_research: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expira_en: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    offers: Mapped[list[Offer]] = relationship("Offer", back_populates="company")


class Offer(Base):
    """A scraped job offer."""

    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("hash_unico", name="uq_offers_hash_unico"),
        Index("ix_offers_user_id", "user_id"),
        Index("ix_offers_estado", "estado"),
        Index("ix_offers_fecha_detectada", "fecha_detectada"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=True
    )
    titulo: Mapped[str] = mapped_column(String(512), nullable=False)
    empresa: Mapped[str] = mapped_column(String(512), nullable=False)
    ubicacion: Mapped[str | None] = mapped_column(String(256), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    fuente: Mapped[str] = mapped_column(String(64), nullable=False)
    fecha_publicacion: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_detectada: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    hash_unico: Mapped[str] = mapped_column(String(64), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default=OfferEstado.nueva)
    razon_descarte: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[Any] = mapped_column(JSON, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="offers")
    company: Mapped[Company | None] = relationship("Company", back_populates="offers")
    evaluation: Mapped[Evaluation | None] = relationship(
        "Evaluation", back_populates="offer", uselist=False
    )
    drafts: Mapped[list[Draft]] = relationship("Draft", back_populates="offer")
    applications: Mapped[list[Application]] = relationship("Application", back_populates="offer")


class Evaluation(Base):
    """Viability evaluation of an offer."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    offer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("offers.id"), nullable=False, unique=True
    )
    puntuacion: Mapped[int] = mapped_column(Integer, nullable=False)
    pros: Mapped[Any] = mapped_column(JSON, nullable=True)
    contras: Mapped[Any] = mapped_column(JSON, nullable=True)
    recomendacion: Mapped[str] = mapped_column(String(32), nullable=False)
    razonamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    offer: Mapped[Offer] = relationship("Offer", back_populates="evaluation")


class Draft(Base):
    """Generated application draft awaiting human review."""

    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    offer_id: Mapped[int] = mapped_column(Integer, ForeignKey("offers.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    asunto: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cuerpo_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    carta_presentacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default=DraftEstado.pendiente)
    intento_num: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    offer: Mapped[Offer] = relationship("Offer", back_populates="drafts")
    user: Mapped[User] = relationship("User", back_populates="drafts")
    application: Mapped[Application | None] = relationship(
        "Application", back_populates="draft", uselist=False
    )


class Application(Base):
    """Record of a submitted application."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("drafts.id"), nullable=False, unique=True
    )
    offer_id: Mapped[int] = mapped_column(Integer, ForeignKey("offers.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    metodo_envio: Mapped[str] = mapped_column(String(32), nullable=False)
    fecha_envio: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_respuesta: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fecha_respuesta: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    draft: Mapped[Draft] = relationship("Draft", back_populates="application")
    offer: Mapped[Offer] = relationship("Offer", back_populates="applications")


class RunLog(Base):
    """Record of a daily pipeline run."""

    __tablename__ = "run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    fecha_inicio: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ofertas_detectadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ofertas_relevantes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    borradores_generados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errores: Mapped[Any] = mapped_column(JSON, nullable=True)
    tokens_consumidos: Mapped[Any] = mapped_column(JSON, nullable=True)
    coste_estimado_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default=RunEstado.running)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    user: Mapped[User | None] = relationship("User", back_populates="run_logs")


# Re-export enums for convenience
__all__ = [
    "Application",
    "Company",
    "Draft",
    "DraftEstado",
    "Evaluation",
    "MetodoEnvio",
    "Offer",
    "OfferEstado",
    "Recomendacion",
    "RunEstado",
    "RunLog",
    "TipoRespuesta",
    "User",
]
