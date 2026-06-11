"""Build a Langfuse eval dataset from historical offers + v1 evaluations.

Pulls every offer that already has a v1 ``evaluations`` row out of SQLite and turns
it into a dataset item: the offer is the input, the v1 verdict (mapped to
apply/maybe/skip) is the reference label. The same items are always written to a
local ``data/evals/dataset.jsonl`` so the eval harness works without Langfuse; when
Langfuse keys are present they are *also* pushed to a Langfuse dataset.

    uv run python scripts/build_eval_dataset.py --user jorge

The reference label can later be hand-corrected directly in the JSONL (or in the
Langfuse UI) without changing this script.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Make the repo root importable when run as a file (``python scripts/...``).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.base import get_session
from src.db.models import Evaluation, Offer

logger = structlog.get_logger(__name__)

DATASET_NAME = "phase-10.5-evaluate-and-draft"
DEFAULT_OUT = Path("data") / "evals" / "dataset.jsonl"

# v1 evaluations.recomendacion -> graph verdict. Covers both the Recomendacion
# enum (solicitar/considerar/descartar) and the FitAssessment Spanish mapping
# (aplicar/dudar/descartar) so either spelling in the DB maps cleanly.
_RECO_TO_VERDICT: dict[str, str] = {
    "solicitar": "apply",
    "aplicar": "apply",
    "considerar": "maybe",
    "dudar": "maybe",
    "descartar": "skip",
}


@dataclass
class EvalItem:
    """One dataset item: the offer input plus its reference verdict.

    Attributes:
        input: Offer fields the graph + judge need (``offer_id`` drives the run).
        expected_output: Reference verdict (apply/maybe/skip).
        metadata: Provenance (source evaluation id, score, raw recommendation).
    """

    input: dict[str, object]
    expected_output: str
    metadata: dict[str, object]


def _reference_verdict(recomendacion: str) -> str | None:
    """Map a v1 ``recomendacion`` to a graph verdict, or ``None`` if unknown."""
    return _RECO_TO_VERDICT.get(recomendacion.strip().lower())


def build_items(session: Session, username: str | None = None) -> list[EvalItem]:
    """Build dataset items from offers that have a v1 evaluation.

    Args:
        session: Open SQLAlchemy session.
        username: If given, restrict to that profile's offers.

    Returns:
        One ``EvalItem`` per evaluated offer whose recommendation maps to a known
        verdict; offers with an unmappable recommendation are skipped (warned).
    """
    stmt = select(Offer, Evaluation).join(Evaluation, Evaluation.offer_id == Offer.id)
    rows = session.execute(stmt).all()

    items: list[EvalItem] = []
    for offer, evaluation in rows:
        if username is not None and offer.user.username != username:
            continue
        verdict = _reference_verdict(evaluation.recomendacion)
        if verdict is None:
            logger.warning(
                "eval_dataset_skip_unknown_reco",
                offer_id=offer.id,
                recomendacion=evaluation.recomendacion,
            )
            continue
        items.append(
            EvalItem(
                input={
                    "offer_id": offer.id,
                    "username": offer.user.username,
                    "titulo": offer.titulo,
                    "empresa": offer.empresa,
                    "ubicacion": offer.ubicacion,
                    "descripcion": offer.descripcion,
                    "fuente": offer.fuente,
                },
                expected_output=verdict,
                metadata={
                    "source_evaluation_id": evaluation.id,
                    "puntuacion": evaluation.puntuacion,
                    "recomendacion": evaluation.recomendacion,
                },
            )
        )
    return items


def _write_jsonl(items: list[EvalItem], path: Path) -> None:
    """Write items as one JSON object per line, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")


def _push_to_langfuse(items: list[EvalItem], dataset_name: str) -> None:
    """Push items to a Langfuse dataset (no-op import path when keys absent)."""
    from src.graph.observability import langfuse_enabled

    if not langfuse_enabled():
        logger.info("eval_dataset_langfuse_skipped", reason="no_keys")
        return

    from langfuse import get_client

    client = get_client()
    dataset = client.create_dataset(name=dataset_name)
    for item in items:
        # langfuse v4 DatasetClient exposes create_item; its bundled stubs are
        # partial (constitution D-02), so the attribute is invisible to mypy.
        dataset.create_item(  # type: ignore[attr-defined]
            input=item.input,
            expected_output=item.expected_output,
            metadata=item.metadata,
        )
    client.flush()
    logger.info("eval_dataset_pushed_to_langfuse", dataset=dataset_name, count=len(items))


def main() -> None:
    """CLI entry point: build items, write JSONL, optionally push to Langfuse."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=None, help="Restrict to one profile username.")
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    with get_session() as session:
        items = build_items(session, username=args.user)

    if not items:
        raise SystemExit(
            "No evaluated offers found. Seed/run the v1 pipeline first "
            "(e.g. uv run python scripts/seed_demo.py --user jorge)."
        )

    _write_jsonl(items, args.out)
    print(f"Wrote {len(items)} dataset item(s) to {args.out}")

    _push_to_langfuse(items, args.dataset_name)


if __name__ == "__main__":
    main()
