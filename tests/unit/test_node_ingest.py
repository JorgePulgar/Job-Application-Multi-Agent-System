"""Unit tests for the ``ingest_offer`` graph node."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from src.db.models import Offer
from src.graph.nodes.ingest import IngestError, make_ingest_offer
from src.models.fit import ParsedOffer


class _FakeResult:
    def __init__(self, parsed: Any) -> None:
        self.parsed = parsed


class _FakeClient:
    """Records the chat call and returns a preset parsed result."""

    def __init__(self, parsed: Any) -> None:
        self._parsed = parsed
        self.calls: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> _FakeResult:
        self.calls.append(kwargs)
        return _FakeResult(self._parsed)


class _FakeSession:
    def __init__(self, offer: Offer | None) -> None:
        self._offer = offer

    def get(self, _model: type[Offer], _pk: int) -> Offer | None:
        return self._offer


def _session_factory(offer: Offer | None) -> Any:
    @contextmanager
    def factory() -> Iterator[_FakeSession]:
        yield _FakeSession(offer)

    return factory


def _offer(**overrides: Any) -> Offer:
    fields: dict[str, Any] = {
        "titulo": "ML Engineer",
        "empresa": "Acme AI",
        "ubicacion": "Madrid",
        "descripcion": "We need strong Python and PyTorch. No salary listed.",
        "raw_json": {"salary_min": None},
    }
    fields.update(overrides)
    return Offer(**fields)


def _parsed(**overrides: Any) -> ParsedOffer:
    data: dict[str, Any] = {
        "title": "ML Engineer",
        "detected_language": "en",
        "seniority": None,
        "company": "Acme AI",
        "sector": None,
        "location": "Madrid",
        "remote_policy": None,
        "required_skills": ["python", "pytorch"],
        "preferred_skills": [],
        "salary_raw": None,
        "languages": ["english"],
        "contract_type": None,
        "sponsorship_mention": None,
    }
    data.update(overrides)
    return ParsedOffer.model_validate(data)


@pytest.mark.asyncio
async def test_no_salary_yields_none_and_skills_populated() -> None:
    """A JD without salary returns salary_raw=None and non-empty required_skills."""
    client = _FakeClient(_parsed(salary_raw=None, required_skills=["python", "pytorch"]))
    node = make_ingest_offer(client, _session_factory(_offer()))  # type: ignore[arg-type]

    out = await node({"offer_id": 1})

    parsed = out["parsed"]
    assert parsed.salary_raw is None
    assert parsed.required_skills == ["python", "pytorch"]


@pytest.mark.asyncio
async def test_uses_mini_with_parsed_offer_response_format() -> None:
    """The node calls gpt-4o-mini with response_format=ParsedOffer and the JD text."""
    client = _FakeClient(_parsed())
    node = make_ingest_offer(client, _session_factory(_offer()))  # type: ignore[arg-type]

    await node({"offer_id": 1})

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["deployment"] == "mini"
    assert call["response_format"] is ParsedOffer
    assert call["cacheable_system"] is True
    assert "PyTorch" in call["user"]


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["es", "en"])
async def test_detected_language_passthrough(language: str) -> None:
    """The detected language from extraction is surfaced on the parsed offer."""
    client = _FakeClient(_parsed(detected_language=language))
    node = make_ingest_offer(client, _session_factory(_offer()))  # type: ignore[arg-type]

    out = await node({"offer_id": 1})

    assert out["parsed"].detected_language == language


@pytest.mark.asyncio
async def test_missing_offer_raises() -> None:
    """A missing offer row raises IngestError."""
    client = _FakeClient(_parsed())
    node = make_ingest_offer(client, _session_factory(None))  # type: ignore[arg-type]

    with pytest.raises(IngestError):
        await node({"offer_id": 999})


@pytest.mark.asyncio
async def test_invalid_parsed_raises() -> None:
    """A non-ParsedOffer LLM result raises IngestError."""
    client = _FakeClient(None)
    node = make_ingest_offer(client, _session_factory(_offer()))  # type: ignore[arg-type]

    with pytest.raises(IngestError):
        await node({"offer_id": 1})
