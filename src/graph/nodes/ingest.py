"""``ingest_offer`` node: parse a DB offer row into a structured ``ParsedOffer``.

Uses ``gpt-4o-mini`` for cheap, mechanical extraction. Crucially it detects the
offer language into ``ParsedOffer.detected_language`` (``es``/``en``), which every
downstream node and the final draft key off. Missing fields are returned as
``None``/empty -- never invented.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from typing import Any

import structlog
from sqlalchemy.orm import Session

from src.db.base import get_session
from src.db.models import Offer
from src.exceptions import JobAgentError
from src.graph.state import EvaluateDraftState
from src.models.fit import ParsedOffer
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], AbstractContextManager[Session]]
IngestNode = Callable[[EvaluateDraftState], Awaitable[dict[str, ParsedOffer]]]

_PROMPT = "graph_ingest"
_RAW_JSON_MAX = 2000


class IngestError(JobAgentError):
    """Raised when an offer cannot be parsed into a valid ``ParsedOffer``."""


def make_ingest_offer(
    client: AzureOpenAIClient,
    session_factory: SessionFactory = get_session,
) -> IngestNode:
    """Build the ``ingest_offer`` node bound to its dependencies.

    Args:
        client: Azure OpenAI client used for the extraction call.
        session_factory: Callable yielding a context-managed ``Session`` used to
            load the offer row. Defaults to the app session factory.

    Returns:
        The ``ingest_offer`` coroutine LangGraph invokes with the graph state.
    """

    async def ingest_offer(state: EvaluateDraftState) -> dict[str, ParsedOffer]:
        """Load the offer, extract structured fields, and detect its language.

        Args:
            state: Graph state carrying ``offer_id``.

        Returns:
            ``{"parsed": ParsedOffer}`` for the fan-out branches to consume.

        Raises:
            IngestError: If the offer row is missing or the LLM returns an
                invalid ``ParsedOffer``.
        """
        offer_id = state["offer_id"]

        with session_factory() as session:
            offer = session.get(Offer, offer_id)
            if offer is None:
                raise IngestError(f"Offer {offer_id} not found")
            titulo = offer.titulo
            empresa = offer.empresa
            ubicacion = offer.ubicacion
            descripcion = offer.descripcion
            raw_json = offer.raw_json

        system = prompt_loader.load_system(_PROMPT)
        user = prompt_loader.load_user(
            _PROMPT,
            titulo=titulo,
            empresa=empresa,
            ubicacion=ubicacion or "No especificada",
            descripcion=(descripcion or "Sin descripción")[:4000],
            raw_json=_raw_json_text(raw_json),
        )

        result = await client.chat(
            deployment="mini",
            system=system,
            user=user,
            response_format=ParsedOffer,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, ParsedOffer):
            raise IngestError(f"LLM did not return a valid ParsedOffer for offer {offer_id}")

        parsed: ParsedOffer = result.parsed
        logger.info(
            "graph_ingest_done",
            offer_id=offer_id,
            detected_language=parsed.detected_language,
            required_skills=len(parsed.required_skills),
        )
        return {"parsed": parsed}

    return ingest_offer


def _raw_json_text(raw_json: Any) -> str:
    """Render ``raw_json`` as compact, length-capped text for the prompt."""
    if not raw_json:
        return "{}"
    return json.dumps(raw_json, ensure_ascii=False)[:_RAW_JSON_MAX]
