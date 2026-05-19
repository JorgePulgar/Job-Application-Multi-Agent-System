"""SQLAlchemy-compatible enums for the job-agent database."""

from enum import StrEnum


class OfferEstado(StrEnum):
    """Lifecycle state of a scraped job offer."""

    nueva = "nueva"
    filtrada = "filtrada"
    descartada = "descartada"
    investigada = "investigada"
    evaluada = "evaluada"
    borrador_generado = "borrador_generado"
    enviada = "enviada"


class Recomendacion(StrEnum):
    """Viability evaluator recommendation."""

    solicitar = "solicitar"
    considerar = "considerar"
    descartar = "descartar"


class MetodoEnvio(StrEnum):
    """Channel used to submit an application."""

    email = "email"
    portal = "portal"
    linkedin = "linkedin"
    otro = "otro"


class TipoRespuesta(StrEnum):
    """Type of company response after application."""

    sin_respuesta = "sin_respuesta"
    positiva = "positiva"
    negativa = "negativa"
    en_proceso = "en_proceso"


class DraftEstado(StrEnum):
    """Review state of a generated draft."""

    pendiente = "pendiente"
    aprobado = "aprobado"
    rechazado = "rechazado"
    needs_manual_context = "needs_manual_context"


class RunEstado(StrEnum):
    """State of a pipeline run."""

    running = "running"
    completed = "completed"
    failed = "failed"
