"""``extract_sponsorship`` fan-out branch: visa/geo viability signal.

Encodes the skill's visa logic with ``gpt-4o-mini``: does the role need
sponsorship, is it offered, is it geo-viable for someone in Spain (remote-EU or
relocation), what is the working language, and is there a decisive blocker.
Text fields are emitted in the offer's detected language.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from src.exceptions import JobAgentError
from src.graph.state import EvaluateDraftState
from src.models.fit import ParsedOffer, SponsorshipSignal
from src.services import prompt_loader
from src.services.azure_openai import AzureOpenAIClient

logger = structlog.get_logger(__name__)

SponsorshipNode = Callable[[EvaluateDraftState], Awaitable[dict[str, SponsorshipSignal]]]

_PROMPT = "graph_sponsorship"
_IDIOMA_NOMBRE = {"es": "español", "en": "inglés"}


class SponsorshipError(JobAgentError):
    """Raised when the sponsorship signal cannot be produced."""


def make_extract_sponsorship(client: AzureOpenAIClient) -> SponsorshipNode:
    """Build the ``extract_sponsorship`` node bound to its LLM client.

    Args:
        client: Azure OpenAI client used for the gpt-4o-mini call.

    Returns:
        The ``extract_sponsorship`` coroutine LangGraph invokes.
    """

    async def extract_sponsorship(state: EvaluateDraftState) -> dict[str, SponsorshipSignal]:
        """Derive the visa/geo viability signal for the offer.

        Args:
            state: Graph state carrying the ``parsed`` offer.

        Returns:
            ``{"sponsorship": SponsorshipSignal}``.

        Raises:
            SponsorshipError: If the LLM returns an invalid signal.
        """
        parsed: ParsedOffer = state["parsed"]
        system = prompt_loader.load_system(_PROMPT)
        user = prompt_loader.load_user(
            _PROMPT,
            titulo=parsed.title,
            empresa=parsed.company,
            ubicacion=parsed.location or "No especificada",
            remote_policy=parsed.remote_policy or "No especificada",
            idiomas=", ".join(parsed.languages) or "No especificados",
            sponsorship_mention=parsed.sponsorship_mention or "No mencionado",
            idioma=_IDIOMA_NOMBRE[parsed.detected_language],
        )

        result = await client.chat(
            deployment="mini",
            system=system,
            user=user,
            response_format=SponsorshipSignal,
            cacheable_system=True,
        )

        if result.parsed is None or not isinstance(result.parsed, SponsorshipSignal):
            raise SponsorshipError("LLM did not return a valid SponsorshipSignal")

        signal: SponsorshipSignal = result.parsed
        logger.info(
            "graph_sponsorship_done",
            geo_viable=signal.geo_viable_for_spain,
            has_blocker=signal.blocker is not None,
        )
        return {"sponsorship": signal}

    return extract_sponsorship
