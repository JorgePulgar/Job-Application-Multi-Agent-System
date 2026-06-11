"""End-to-end test of the whole compiled ``evaluate_and_draft`` graph.

Runs the real ``build_graph`` topology (ingest -> research fan-out -> assess ->
confidence routing -> human_review -> draft) against fully mocked services for
three offers:

* a clean **APPLY** (straight to review, then a draft);
* a **borderline** that triggers exactly one ``gather_more`` loop then APPLY
  (``loop_count == 1``);
* a hard **SKIP** that ends short -- no draft, the draft node never runs.

No real network/LLM: the Azure client is a dispatching fake, ``CompanyResearcher``
/ ``search_web`` / ``load_profile`` are patched. The human-review interrupt is
auto-resumed by mirroring the model verdict (the orchestrator's autonomous mode).
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.agents.company_researcher import CompanyResearcher
from src.db.base import Base
from src.db.enums import OfferEstado
from src.db.models import Company, Offer, User
from src.graph import nodes as _nodes_pkg  # noqa: F401  (ensures node modules import)
from src.graph.build import build_graph, thread_config
from src.graph.nodes import draft as draft_mod
from src.graph.nodes import gather_more as gather_mod
from src.graph.nodes import match_profile as match_mod
from src.models.company import CompanyDossier
from src.models.fit import (
    CoverLetterDraft,
    FitAssessment,
    ParsedOffer,
    RequirementItem,
    RequirementMatch,
    SponsorshipSignal,
    TailoringPointers,
)
from src.models.search import SearchResult
from src.models.user_profile import LocationPreference, Modality, UserProfile
from src.services.azure_openai import ChatResult, TokenUsage

_COMPANY = "Acme"


def _profile() -> UserProfile:
    return UserProfile(
        username="jorge",
        nombre="Jorge",
        email="jorge@example.com",
        location="Madrid",
        target_roles=["Data Engineer"],
        tech_stack=["python"],
        red_flags=[],
        min_salary=40000,
        location_preference=LocationPreference(modality=Modality.remote),
        cv_summary="CV: Python, pipelines de datos.",
    )


def _parsed() -> ParsedOffer:
    return ParsedOffer.model_validate(
        {
            "title": "Data Engineer",
            "detected_language": "es",
            "seniority": None,
            "company": _COMPANY,
            "sector": None,
            "location": "Madrid",
            "remote_policy": "remote",
            "required_skills": ["python"],
            "preferred_skills": [],
            "salary_raw": None,
            "languages": ["español"],
            "contract_type": None,
            "sponsorship_mention": None,
        }
    )


def _dossier() -> CompanyDossier:
    return CompanyDossier.model_validate(
        {
            "sector": "data",
            "tamano": "pyme",
            "ubicacion_hq": "Madrid",
            "descripcion": "Plataforma de datos.",
            "stack_tecnologico": ["python"],
            "cultura_notas": [],
            "red_flags_detectadas": [],
            "productos_o_servicios": ["plataforma de datos"],
            "equipo_ai_detectado": True,
            "fuentes": [],
        }
    )


def _sponsorship() -> SponsorshipSignal:
    return SponsorshipSignal(
        needs_sponsorship=False,
        sponsorship_offered=None,
        geo_viable_for_spain=True,
        working_language="español",
        blocker=None,
    )


def _requirements() -> RequirementMatch:
    return RequirementMatch(
        items=[RequirementItem(requirement="python", status="met", note="ok")],
        standout_points=["pipelines en Python"],
        gaps=[],
    )


def _fit(recommendation: str, *, missing: list[str]) -> FitAssessment:
    return FitAssessment(
        fit_level="strong" if recommendation == "apply" else "weak",
        recommendation=recommendation,  # type: ignore[arg-type]
        score=85 if recommendation == "apply" else 30,
        reasoning="Razón decisiva.",
        red_flags=[],
        missing_info=missing,
        tailoring=TailoringPointers(
            cv_emphasis=["pipelines en Python"],
            cover_letter_hook="vuestra plataforma de datos",
            gap_to_address=None,
        )
        if recommendation != "skip"
        else None,
    )


_CLEAN_BODY = (
    "Hola, escribo por la vacante en Acme. Vuestra plataforma de datos encaja con "
    "mi experiencia construyendo pipelines en Python, donde reduje un 30% el tiempo "
    "de proceso. Me gustaría aportar ese trabajo a vuestro equipo. Un saludo."
)


def _draft() -> CoverLetterDraft:
    return CoverLetterDraft(
        subject="Candidatura Data Engineer en Acme",
        body=_CLEAN_BODY,
        lead_angle="vuestra plataforma de datos",
        hook="plataforma de datos",
    )


class _GraphClient:
    """Dispatching fake Azure client: returns the right schema per response_format."""

    def __init__(self) -> None:
        self.fit_seq: list[FitAssessment] = []
        self.seen: list[str] = []

    async def chat(self, *, response_format: Any = None, **_kw: Any) -> ChatResult:
        name = response_format.__name__ if response_format is not None else "text"
        self.seen.append(name)
        parsed = self._dispatch(name)
        return ChatResult(
            content="",
            parsed=parsed,
            usage=TokenUsage(prompt_tokens=0, cached_tokens=0, completion_tokens=0, total_tokens=0),
            latency_ms=0.0,
            model="mock",
        )

    def _dispatch(self, name: str) -> Any:
        if name == "ParsedOffer":
            return _parsed()
        if name == "SponsorshipSignal":
            return _sponsorship()
        if name == "RequirementMatch":
            return _requirements()
        if name == "FitAssessment":
            return self.fit_seq.pop(0)
        if name == "CoverLetterDraft":
            return _draft()
        raise AssertionError(f"unexpected response_format {name}")


@pytest.fixture()
def db_engine() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="jorge", nombre="Jorge")
        session.add(user)
        session.flush()
        co = Company(nombre=_COMPANY, sector="data", descripcion="Plataforma de datos.")
        session.add(co)
        session.flush()
        for i in range(3):
            session.add(
                Offer(
                    user_id=user.id,
                    company_id=co.id,
                    titulo="Data Engineer",
                    empresa=_COMPANY,
                    fuente="adzuna",
                    hash_unico=f"e2e-{i}",
                    estado=OfferEstado.investigada,
                    descripcion="Rol de datos.",
                )
            )
        session.commit()
    return engine


async def _run_offer(graph: Any, client: _GraphClient, offer_id: int) -> dict[str, Any]:
    """Invoke the graph for one offer, auto-resuming the review interrupt."""
    cfg = thread_config("jorge", offer_id)
    result = await graph.ainvoke({"offer_id": offer_id, "username": "jorge"}, config=cfg)
    if "__interrupt__" in result:
        fit: FitAssessment = (await graph.aget_state(cfg)).values["fit"]
        await graph.ainvoke(
            Command(
                resume={"decision": fit.recommendation, "lead_angle": None, "clarifications": {}}
            ),
            config=cfg,
        )
    return dict((await graph.aget_state(cfg)).values)


@pytest.mark.asyncio
async def test_whole_graph_apply_borderline_skip(
    db_engine: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One compiled graph over three offers: APPLY, borderline+1 loop, hard SKIP."""
    client = _GraphClient()

    monkeypatch.setattr(match_mod, "load_profile", lambda _u: _profile())
    monkeypatch.setattr(draft_mod, "load_profile", lambda _u: _profile())
    monkeypatch.setattr(
        gather_mod,
        "search_web",
        AsyncMock(return_value=[SearchResult(title="t", url="u", snippet="dato extra")]),
    )

    @contextlib.contextmanager
    def _sf() -> Iterator[Session]:
        with Session(db_engine) as s:
            yield s

    with patch.object(CompanyResearcher, "research", AsyncMock(return_value=_dossier())):
        graph = build_graph(MemorySaver(), client=client, session_factory=_sf)  # type: ignore[arg-type]

        # --- Offer 1: clean APPLY ---
        client.fit_seq = [_fit("apply", missing=[])]
        before = len(client.seen)
        vals = await _run_offer(graph, client, 1)
        assert vals["fit"].recommendation == "apply"
        assert vals.get("loop_count", 0) == 0
        assert vals.get("draft") is not None
        assert vals["needs_manual_context"] is False
        assert "CoverLetterDraft" in client.seen[before:]

        # --- Offer 2: borderline -> one gather_more loop -> APPLY ---
        client.fit_seq = [_fit("maybe", missing=["¿rango salarial?"]), _fit("apply", missing=[])]
        vals = await _run_offer(graph, client, 2)
        assert vals["loop_count"] == 1
        assert vals["fit"].recommendation == "apply"
        assert vals.get("draft") is not None

        # --- Offer 3: hard SKIP -> ends short, no draft, draft node never ran ---
        client.fit_seq = [_fit("skip", missing=[])]
        before = len(client.seen)
        vals = await _run_offer(graph, client, 3)
        assert vals["fit"].recommendation == "skip"
        assert vals.get("draft") is None
        assert "CoverLetterDraft" not in client.seen[before:]
