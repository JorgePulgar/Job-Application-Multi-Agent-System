"""Run the ``evaluate_and_draft`` subgraph over the eval dataset and score it.

For each dataset item the subgraph runs end-to-end (auto-resuming the human-review
interrupt by *mirroring the model's own verdict*, so we measure the model and not a
human override). Three scores are computed per item -- verdict agreement,
faithfulness (LLM judge), specificity -- and either recorded to Langfuse (when keys
are present) or printed and saved to ``data/evals/`` (when they are not).

    uv run python scripts/build_eval_dataset.py --user jorge   # build the dataset
    uv run python scripts/run_eval.py --write-baseline         # first baseline run

``--write-baseline`` overwrites ``docs/eval-baseline.md`` with this run's numbers as
the baseline to beat. Both the offers and the dataset must come from the same
SQLite DB (the graph loads each offer by ``offer_id``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Make the repo root importable when run as a file (``python scripts/...``).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog
from dotenv import load_dotenv

load_dotenv()

from langgraph.types import Command  # noqa: E402

from src.graph import observability as o  # noqa: E402
from src.graph.build import build_graph, open_checkpointer  # noqa: E402
from src.graph.evals import (  # noqa: E402
    FaithfulnessJudge,
    ScoreResult,
    score_specificity,
    score_verdict_agreement,
)
from src.models.company import CompanyDossier  # noqa: E402
from src.models.fit import CoverLetterDraft, FitAssessment, ParsedOffer  # noqa: E402
from src.services.azure_openai import AzureOpenAIClient  # noqa: E402

logger = structlog.get_logger(__name__)

DEFAULT_DATASET = Path("data") / "evals" / "dataset.jsonl"
EVAL_CHECKPOINT_DB = Path("data") / "evals" / "eval_checkpoints.db"
RESULTS_DIR = Path("data") / "evals"
BASELINE_DOC = Path("docs") / "eval-baseline.md"


def _load_items(path: Path) -> list[dict[str, Any]]:
    """Load dataset items from a JSONL file."""
    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}. Run scripts/build_eval_dataset.py first.")
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _offer_text(parsed: ParsedOffer, descripcion: str | None) -> str:
    """Render the offer as a compact source text for the faithfulness judge."""
    skills = ", ".join(parsed.required_skills) or "—"
    return (
        f"Título: {parsed.title}\n"
        f"Empresa: {parsed.company}\n"
        f"Ubicación: {parsed.location or '—'}\n"
        f"Requisitos: {skills}\n"
        f"Descripción: {(descripcion or '')[:2000]}"
    )


def _thread_id(run_name: str, offer_id: int, username: str) -> str:
    """Per-run thread id so a rerun never resumes a previous run's finished thread."""
    return f"{run_name}:{offer_id}:{username}"


async def _run_item(graph: Any, item: dict[str, Any], run_name: str) -> dict[str, Any]:
    """Run the subgraph for one item and return its final state values.

    Auto-resumes the human-review interrupt by mirroring the model's verdict.
    """
    offer_id = int(item["input"]["offer_id"])
    username = str(item["input"]["username"])
    cfg = {"configurable": {"thread_id": _thread_id(run_name, offer_id, username)}}

    result = await graph.ainvoke({"offer_id": offer_id, "username": username}, config=cfg)
    if "__interrupt__" in result:
        snapshot = await graph.aget_state(cfg)
        fit: FitAssessment = snapshot.values["fit"]
        # Mirror the model's own verdict so the eval measures the model, not a human.
        await graph.ainvoke(
            Command(
                resume={
                    "decision": fit.recommendation,
                    "lead_angle": None,
                    "clarifications": {},
                }
            ),
            config=cfg,
        )

    final = await graph.aget_state(cfg)
    return dict(final.values)


async def _score_item(
    item: dict[str, Any],
    values: dict[str, Any],
    judge: FaithfulnessJudge,
) -> list[ScoreResult]:
    """Compute the three scores for one completed item."""
    parsed: ParsedOffer = values["parsed"]
    fit: FitAssessment = values["fit"]
    dossier: CompanyDossier | None = values.get("dossier")
    draft: CoverLetterDraft | None = values.get("draft")

    scores: list[ScoreResult] = [
        score_verdict_agreement(fit.recommendation, str(item["expected_output"])),  # type: ignore[arg-type]
    ]
    spec = score_specificity(draft, dossier=dossier, empresa=parsed.company)
    if spec is not None:
        scores.append(spec)
    scores.append(
        await judge.score(
            oferta_text=_offer_text(parsed, item["input"].get("descripcion")),
            dossier_text=dossier.to_summary_for_prompt() if dossier else "(sin dossier)",
            reasoning=fit.reasoning,
            draft_body=draft.body if draft else None,
        )
    )
    return scores


def _record_langfuse(scores: list[ScoreResult]) -> None:
    """Attach scores to the current Langfuse trace (no-op when disabled)."""
    if not o.langfuse_enabled():
        return
    from langfuse import get_client

    client = get_client()
    for s in scores:
        client.score_current_trace(name=s.name, value=s.value, comment=s.comment)


def _aggregate(per_item: list[dict[str, Any]]) -> dict[str, float]:
    """Mean of each score name across items that have it."""
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for row in per_item:
        for name, value in row["scores"].items():
            sums[name] = sums.get(name, 0.0) + value
            counts[name] = counts.get(name, 0) + 1
    return {name: round(sums[name] / counts[name], 4) for name in sums}


def _fmt(aggregate: dict[str, float], name: str) -> str:
    """Format a score, or ``n/a`` when it was never measured this run."""
    return f"{aggregate[name]:.3f}" if name in aggregate else "n/a (not measured this run)"


def _write_baseline(run_name: str, count: int, aggregate: dict[str, float]) -> None:
    """Write docs/eval-baseline.md with this run's aggregate as the baseline."""
    lines = [
        "# Eval baseline — `evaluate_and_draft` subgraph",
        "",
        "First scored run of the Phase 10.5 subgraph against the historical-offer",
        "dataset. These are the numbers to beat: a later prompt/graph change should",
        "raise (or hold) every score. Regenerate with:",
        "",
        "```bash",
        "uv run python scripts/build_eval_dataset.py --user jorge",
        "uv run python scripts/run_eval.py --write-baseline",
        "```",
        "",
        "## Scores",
        "",
        "Each score is the mean over the dataset, in `[0, 1]`.",
        "",
        "| Score | Meaning | Baseline |",
        "| --- | --- | --- |",
        "| `verdict_agreement` | Graph verdict vs reference (1 exact, 0.5 near-miss) | "
        f"{_fmt(aggregate, 'verdict_agreement')} |",
        "| `faithfulness` | No invented company/offer facts (LLM judge, gpt-4o) | "
        f"{_fmt(aggregate, 'faithfulness')} |",
        "| `specificity` | Draft cites ≥1 concrete company fact (drafted items only) | "
        f"{_fmt(aggregate, 'specificity')} |",
        "",
        f"Run `{run_name}` over {count} item(s).",
        "",
    ]
    BASELINE_DOC.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_DOC.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote baseline to {BASELINE_DOC}")


async def run(dataset: Path, write_baseline: bool) -> None:
    """Execute the eval run over the dataset and emit scores."""
    o.init_langfuse()
    items = _load_items(dataset)
    client = AzureOpenAIClient()
    judge = FaithfulnessJudge(client)
    run_name = f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"

    per_item: list[dict[str, Any]] = []
    async with open_checkpointer(EVAL_CHECKPOINT_DB) as saver:
        graph = build_graph(saver, client=client)
        for item in items:
            offer_id = int(item["input"]["offer_id"])
            username = str(item["input"]["username"])
            thread_id = _thread_id(run_name, offer_id, username)
            async with o.trace_run(thread_id, username=username, offer_id=offer_id):
                values = await _run_item(graph, item, run_name)
                scores = await _score_item(item, values, judge)
                _record_langfuse(scores)
            per_item.append(
                {
                    "offer_id": offer_id,
                    "prediction": values["fit"].recommendation,
                    "reference": item["expected_output"],
                    "scores": {s.name: s.value for s in scores},
                }
            )
            logger.info("eval_item_done", offer_id=offer_id)

    aggregate = _aggregate(per_item)

    print(f"\n=== {run_name} — {len(per_item)} item(s) ===")
    for name, value in aggregate.items():
        print(f"  {name:18s} {value:.3f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{run_name}.json"
    out.write_text(
        json.dumps({"run": run_name, "aggregate": aggregate, "items": per_item}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved run to {out}")

    if write_baseline:
        _write_baseline(run_name, len(per_item), aggregate)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Overwrite docs/eval-baseline.md with this run's numbers.",
    )
    args = parser.parse_args()
    asyncio.run(run(args.dataset, args.write_baseline))


if __name__ == "__main__":
    main()
