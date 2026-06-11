"""Unit tests for the Phase 10.5 eval scorers + dataset builder.

Scorers are tested on crafted (prediction, reference) and (draft, dossier) pairs;
the faithfulness judge is tested with a mocked LLM client; the dataset builder is
tested against a seeded in-memory SQLite DB.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scripts.build_eval_dataset import build_items
from src.db.base import Base
from src.db.models import Company, Evaluation, Offer, User
from src.graph.evals import (
    FAITHFULNESS,
    SPECIFICITY,
    VERDICT_AGREEMENT,
    FaithfulnessJudge,
    FaithfulnessVerdict,
    score_specificity,
    score_verdict_agreement,
)
from src.models.company import CompanyDossier
from src.models.fit import CoverLetterDraft

# --- verdict agreement -----------------------------------------------------


def test_verdict_exact_match_scores_one() -> None:
    result = score_verdict_agreement("apply", "apply")
    assert result.name == VERDICT_AGREEMENT
    assert result.value == 1.0


def test_verdict_apply_vs_maybe_is_half() -> None:
    assert score_verdict_agreement("apply", "maybe").value == 0.5
    assert score_verdict_agreement("maybe", "apply").value == 0.5


def test_verdict_skip_mismatch_scores_zero() -> None:
    assert score_verdict_agreement("apply", "skip").value == 0.0
    assert score_verdict_agreement("skip", "maybe").value == 0.0


# --- specificity -----------------------------------------------------------


def _dossier() -> CompanyDossier:
    return CompanyDossier(
        sector="IA",
        ubicacion_hq="Madrid, España",
        descripcion="Plataforma de analítica.",
        stack_tecnologico=["pytorch", "kubernetes"],
        productos_o_servicios=["Plataforma SaaS"],
    )


def test_specificity_none_draft_returns_none() -> None:
    assert score_specificity(None, dossier=_dossier(), empresa="NeuralForge") is None


def test_specificity_pass_when_company_and_fact_cited() -> None:
    draft = CoverLetterDraft(
        subject="Candidatura",
        body="En NeuralForge me encaja vuestro uso de pytorch en producción.",
        lead_angle="pytorch en producción",
        hook="pytorch",
    )
    result = score_specificity(draft, dossier=_dossier(), empresa="NeuralForge")
    assert result is not None
    assert result.name == SPECIFICITY
    assert result.value == 1.0


def test_specificity_fail_when_generic() -> None:
    draft = CoverLetterDraft(
        subject="Candidatura",
        body="Me interesa mucho la oferta y creo que encajo bien.",
        lead_angle="interés",
        hook="—",
    )
    result = score_specificity(draft, dossier=_dossier(), empresa="NeuralForge")
    assert result is not None
    assert result.value == 0.0


# --- faithfulness judge ----------------------------------------------------


@pytest.mark.asyncio
async def test_faithfulness_judge_scales_score() -> None:
    verdict = FaithfulnessVerdict(score=80, unsupported_claims=[], comment="todo fundamentado")
    client = MagicMock()
    client.chat = AsyncMock(return_value=SimpleNamespace(parsed=verdict))

    judge = FaithfulnessJudge(client)
    result = await judge.score(
        oferta_text="oferta",
        dossier_text="dossier",
        reasoning="razonamiento",
        draft_body="cuerpo",
    )
    assert result.name == FAITHFULNESS
    assert result.value == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_faithfulness_judge_lists_unsupported_in_comment() -> None:
    verdict = FaithfulnessVerdict(
        score=20, unsupported_claims=["factura 10M€"], comment="cifra inventada"
    )
    client = MagicMock()
    client.chat = AsyncMock(return_value=SimpleNamespace(parsed=verdict))

    result = await FaithfulnessJudge(client).score(
        oferta_text="o", dossier_text="d", reasoning="r", draft_body=None
    )
    assert result.value == pytest.approx(0.2)
    assert "factura 10M€" in result.comment


# --- dataset builder -------------------------------------------------------


@pytest.fixture()
def seeded_session() -> Any:
    """In-memory DB: one user, two evaluated offers (one mappable, one not)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()
        co = Company(nombre="NeuralForge", sector="IA", descripcion="Tech.")
        session.add(co)
        session.flush()

        good = Offer(
            user_id=user.id,
            company_id=co.id,
            titulo="ML Engineer",
            empresa="NeuralForge",
            ubicacion="Madrid",
            descripcion="Stack: pytorch.",
            fuente="adzuna",
            hash_unico="h-good",
        )
        bad = Offer(
            user_id=user.id,
            company_id=co.id,
            titulo="Data Engineer",
            empresa="NeuralForge",
            ubicacion="Barcelona",
            descripcion="Stack: spark.",
            fuente="jooble",
            hash_unico="h-bad",
        )
        session.add_all([good, bad])
        session.flush()
        session.add_all(
            [
                Evaluation(offer_id=good.id, puntuacion=85, recomendacion="solicitar"),
                Evaluation(offer_id=bad.id, puntuacion=50, recomendacion="???"),
            ]
        )
        session.commit()
        yield session


def test_build_items_maps_reference_and_skips_unknown(seeded_session: Session) -> None:
    items = build_items(seeded_session, username="jorge")

    # Only the offer with a mappable recommendation becomes an item.
    assert len(items) == 1
    item = items[0]
    assert item.expected_output == "apply"
    assert item.input["empresa"] == "NeuralForge"
    assert item.input["username"] == "jorge"
    assert isinstance(item.input["offer_id"], int)
    assert item.metadata["recomendacion"] == "solicitar"


def test_build_items_filters_by_username(seeded_session: Session) -> None:
    assert build_items(seeded_session, username="otro") == []
