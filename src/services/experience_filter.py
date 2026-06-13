"""Experience-level search biasing and post-fetch filtering for scrapers.

Pure string/regex heuristics — no LLM. Two responsibilities:

1. :func:`query_terms` — the seniority keywords to bias a platform search query
   toward the user's level (e.g. add ``junior``/``becario``/``entry level``).
2. :func:`matches` — a conservative post-fetch filter that drops only offers
   that *explicitly* require more years than the level allows (stealth-senior:
   a "junior" search returning "5+ years required").

Both reuse the level → keywords / year-range mappings defined on
:class:`~src.models.user_profile.ExperienceLevel`, so there is one source of
truth.
"""

from __future__ import annotations

import re
import unicodedata

from src.models.user_profile import ExperienceLevel

# Numbers immediately followed by a years-of-experience word, in es or en
# (accent-stripped, lowercased). Captures the adjacent figure; for ranges like
# "3-5 years" the higher number is captured, which is sufficient — we only need
# to know whether the requirement clears the level's ceiling.
_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:anos?|years?|yrs?)\b")


def _ascii_lower(text: str) -> str:
    """Lowercase and strip accents for accent-insensitive matching."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def query_terms(level: ExperienceLevel) -> list[str]:
    """Return the union of es + en seniority keywords for *level*.

    Order-stable and de-duplicated. Used to bias a search query (Adzuna
    ``what_or`` / Jooble ``keywords``) toward the requested seniority.
    """
    terms: list[str] = []
    for lang in ("es", "en"):
        for kw in level.keywords(lang):
            if kw not in terms:
                terms.append(kw)
    return terms


def _required_min_years(text: str) -> int | None:
    """Return the smallest "N years/años" figure mentioned in *text*, else None.

    Taking the minimum keeps the filter conservative: an offer is only dropped
    when even the lowest stated requirement exceeds the level's ceiling.
    """
    nums = [int(m) for m in _YEARS_RE.findall(_ascii_lower(text))]
    return min(nums) if nums else None


def matches(level: ExperienceLevel, title: str, description: str) -> bool:
    """Return ``True`` if an offer is compatible with *level*.

    Conservative — drops only on an explicit years requirement above the level's
    maximum (e.g. a junior search hitting "minimum 4 years"). Offers with no
    stated requirement, or a senior level (open-ended ceiling), are always kept.

    Args:
        level: The user's target seniority.
        title: Offer title.
        description: Offer description / snippet.

    Returns:
        Whether to keep the offer.
    """
    _, max_years = level.year_range
    if max_years is None:
        return True  # senior: open-ended ceiling, never drop on years
    required = _required_min_years(f"{title} {description}")
    return required is None or required <= max_years
