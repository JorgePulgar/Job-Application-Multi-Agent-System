"""Unit tests for the WTTJ scraper — pure parsing functions only, no Playwright."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.job_scraper.wttj import (
    _infer_modalidad_from_tags,
    cards_to_offers,
    parse_job_cards,
)
from src.models.job_offer import Modalidad

_HTML = (Path(__file__).parent.parent / "fixtures" / "wttj_listing.html").read_text(
    encoding="utf-8"
)


# ---------------------------------------------------------------------------
# _infer_modalidad_from_tags
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tags, expected",
    [
        (["CDI", "Full Remote"], Modalidad.remote),
        (["CDI", "Remoto"], Modalidad.remote),
        (["CDI", "Hibrido"], Modalidad.hybrid),
        (["CDI", "Hybrid"], Modalidad.hybrid),
        (["CDI", "Presencial"], Modalidad.onsite),
        (["CDI"], Modalidad.unknown),
        ([], Modalidad.unknown),
    ],
)
def test_infer_modalidad_from_tags(tags: list[str], expected: Modalidad) -> None:
    assert _infer_modalidad_from_tags(tags) == expected


# ---------------------------------------------------------------------------
# parse_job_cards — HTML fixture
# ---------------------------------------------------------------------------


def test_parse_returns_three_valid_cards() -> None:
    """The broken card (missing title) should be silently skipped."""
    cards = parse_job_cards(_HTML)
    assert len(cards) == 3


def test_parse_first_card_fields() -> None:
    cards = parse_job_cards(_HTML)
    first = cards[0]
    assert first["titulo"] == "ML Engineer"
    assert first["empresa"] == "Acme Fintech SL"
    assert first["ubicacion"] == "Madrid"
    assert "welcometothejungle.com" in first["url"]
    assert "Full Remote" in first["tags"]


def test_parse_url_is_absolute() -> None:
    cards = parse_job_cards(_HTML)
    for card in cards:
        assert card["url"].startswith("https://"), f"Non-absolute URL: {card['url']}"


def test_parse_tags_extracted() -> None:
    cards = parse_job_cards(_HTML)
    assert "45K-65K EUR" in cards[0]["tags"]
    assert "Hibrido" in cards[1]["tags"]
    assert "Presencial" in cards[2]["tags"]


def test_parse_empty_html() -> None:
    cards = parse_job_cards("<html><body></body></html>")
    assert cards == []


def test_parse_no_selector_match_skipped(caplog: pytest.LogCaptureFixture) -> None:
    """Cards without a title element are skipped with a warning."""
    html = """
    <article data-testid="job-card">
      <p data-testid="company-name">Broken Corp</p>
    </article>
    """
    import logging

    with caplog.at_level(logging.WARNING):
        cards = parse_job_cards(html)
    assert cards == []


# ---------------------------------------------------------------------------
# cards_to_offers — integration of parse + map
# ---------------------------------------------------------------------------


def test_cards_to_offers_count() -> None:
    cards = parse_job_cards(_HTML)
    offers = cards_to_offers(cards)
    assert len(offers) == 3


def test_cards_to_offers_modalidad() -> None:
    cards = parse_job_cards(_HTML)
    offers = cards_to_offers(cards)
    assert offers[0].modalidad == Modalidad.remote
    assert offers[1].modalidad == Modalidad.hybrid
    assert offers[2].modalidad == Modalidad.onsite


def test_cards_to_offers_plataforma() -> None:
    cards = parse_job_cards(_HTML)
    offers = cards_to_offers(cards)
    assert all(o.plataforma == "wttj" for o in offers)


def test_cards_to_offers_hash_unique() -> None:
    cards = parse_job_cards(_HTML)
    offers = cards_to_offers(cards)
    hashes = [o.hash_unico for o in offers]
    assert len(hashes) == len(set(hashes))
