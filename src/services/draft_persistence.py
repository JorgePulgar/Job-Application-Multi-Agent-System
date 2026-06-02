"""Persist generated drafts to the database and to markdown files on disk.

Each draft is stored once per offer in the ``drafts`` table (idempotent: a second
save updates the existing row) and mirrored to
``data/drafts/{username}/{YYYY-MM-DD}_{slug}.md`` for offline review.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.enums import OfferEstado
from src.db.models import Draft as DbDraft
from src.db.models import Offer
from src.models.draft import Draft
from src.models.user_profile import UserProfile

logger = structlog.get_logger(__name__)

_DRAFTS_ROOT = Path("data") / "drafts"
_SLUG_MAX_LEN = 80


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def slugify(text: str) -> str:
    """Return a filesystem-safe slug: folded, lowercased, non-alphanumerics to ``_``.

    Args:
        text: Arbitrary text (company name, title).

    Returns:
        A slug containing only ``[a-z0-9_]``, collapsed and trimmed, never empty.
    """
    folded = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", folded).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug or "draft"


def _draft_filename(offer: Offer, when: datetime.date) -> str:
    """Build ``{YYYY-MM-DD}_{slug}.md`` from the offer's company and title."""
    slug = slugify(f"{offer.empresa}_{offer.titulo}")[:_SLUG_MAX_LEN].strip("_") or "draft"
    return f"{when.isoformat()}_{slug}.md"


def _frontmatter(draft: Draft, offer: Offer) -> str:
    """Render the YAML frontmatter block for the markdown file."""
    score: int | str = offer.evaluation.puntuacion if offer.evaluation else "N/A"
    recomendacion = offer.evaluation.recomendacion if offer.evaluation else "N/A"
    lines = [
        "---",
        f"offer_url: {offer.url or ''}",
        f"empresa: {offer.empresa}",
        f"score: {score}",
        f"recomendacion: {recomendacion}",
        f"needs_manual_context: {str(draft.needs_manual_context).lower()}",
        "---",
    ]
    return "\n".join(lines)


def _markdown(draft: Draft, offer: Offer) -> str:
    """Render the full markdown document for a draft."""
    parts = [_frontmatter(draft, offer), ""]

    if draft.needs_manual_context:
        parts.append("> ⚠️ **NECESITA CONTEXTO MANUAL**")
        if draft.flagged_reasons:
            parts.append(">")
            parts += [f"> - {reason}" for reason in draft.flagged_reasons]
        parts.append("")

    parts += [
        f"# {offer.titulo} — {offer.empresa}",
        "",
        "## Asunto",
        draft.email_subject or "_(sin asunto)_",
        "",
        "## Cuerpo del email",
        draft.email_body or "_(sin cuerpo)_",
        "",
        "## Carta de presentación",
        draft.carta_presentacion or "_(no se generó carta)_",
        "",
        "## Experiencias destacadas",
    ]
    parts += [f"- {exp}" for exp in draft.experiencias_destacadas] or ["_(ninguna)_"]
    parts.append("")
    return "\n".join(parts)


def _upsert_db_row(draft: Draft, offer: Offer, session: Session) -> DbDraft:
    """Insert or update the single ``drafts`` row for this offer (idempotent)."""
    existing = session.scalars(select(DbDraft).where(DbDraft.offer_id == offer.id)).first()
    new_row = draft.to_db_row(offer_id=offer.id, user_id=offer.user_id)

    if existing is None:
        new_row.updated_at = _now()
        session.add(new_row)
        return new_row

    existing.asunto = new_row.asunto
    existing.cuerpo_email = new_row.cuerpo_email
    existing.carta_presentacion = new_row.carta_presentacion
    existing.estado = new_row.estado
    existing.intento_num += 1
    existing.updated_at = _now()
    return existing


def save_draft(draft: Draft, offer: Offer, user: UserProfile, db_session: Session) -> Path:
    """Persist a draft to the database and to a markdown file.

    The DB write is idempotent on ``offer_id`` (one draft per offer; a repeat save
    updates the existing row). The offer ``estado`` moves to ``borrador_generado``
    for a complete draft, or stays ``evaluada`` when flagged ``needs_manual_context``.

    Args:
        draft: The generated draft (possibly flagged).
        offer: The DB offer the draft answers (attached to ``db_session``).
        user: The user profile (used for the per-user folder).
        db_session: Active session; the caller owns commit/rollback.

    Returns:
        Path to the written markdown file.
    """
    _upsert_db_row(draft, offer, db_session)
    if not draft.needs_manual_context:
        offer.estado = OfferEstado.borrador_generado
    db_session.flush()

    out_dir = _DRAFTS_ROOT / user.username
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _draft_filename(offer, _now().date())
    path.write_text(_markdown(draft, offer), encoding="utf-8")

    logger.info(
        "draft_saved",
        offer_id=offer.id,
        username=user.username,
        needs_manual_context=draft.needs_manual_context,
        path=str(path),
    )
    return path
