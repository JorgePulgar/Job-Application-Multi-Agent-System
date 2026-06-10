"""Post-generation lint for application drafts.

Enforces, after the LLM returns a draft:

* the prohibited-words list (CLAUDE.md + Jorge's voice rules), accent-folded;
* the zero em-dash / en-dash rule (the strictest voice rule);
* a specificity rule (the body must reference the company by name plus at least
  one concrete fact from the research dossier);
* the no-AI-disclosure rule (the body must not say it was written by an AI).

No draft text is logged; only a short body hash plus issue reasons.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

import structlog

from src.models.company import CompanyDossier
from src.models.draft import Draft
from src.models.fit import CoverLetterDraft

logger = structlog.get_logger(__name__)

# Em-dash (U+2014) and en-dash (U+2013): the strictest voice rule.
_EM_DASH = "—"
_EN_DASH = "–"  # noqa: RUF001

# Generic company-name suffixes ignored when matching the name in the body.
_NAME_STOPWORDS = frozenset(
    {"sl", "s.l.", "sa", "s.a.", "slu", "inc", "llc", "ltd", "corp", "gmbh", "bv", "the", "group"}
)

# Words too short or generic to count as a name token.
_MIN_TOKEN_LEN = 3

# Prohibited words/phrases. Stored accent-folded + lowercased for matching.
_PROHIBITED_RAW: tuple[str, ...] = (
    # Spanish AI-tells / clichés
    "apasionado",
    "apasionada",
    "proactivo",
    "proactiva",
    "jugador de equipo",
    "orientado a resultados",
    "orientada a resultados",
    "dinámico",
    "robusto",
    "sin fisuras",
    "sinergia",
    "panorama",
    "desbloquear",
    "en última instancia",
    "ritmo frenético",
    "impulsado por resultados",
    # English AI-tells
    "leverage",
    "robust",
    "seamless",
    "pivotal",
    "crucial",
    "underscore",
    "showcase",
    "delve",
    "landscape",
    "journey",
    "unlock",
    "harness",
    "embark",
    "illuminate",
    "tapestry",
    "realm",
    "passionate",
    "fast-paced",
    "results-driven",
    "synergy",
    "ultimately",
    "indeed",
)

# English banned-cliché list (Phase 10.5). The combined list above is applied to
# Spanish drafts; English drafts use this list: the English AI-tells plus the
# extra clichés the graph draft node must reject.
_PROHIBITED_EN_RAW: tuple[str, ...] = (
    "leverage",
    "robust",
    "seamless",
    "pivotal",
    "crucial",
    "underscore",
    "showcase",
    "delve",
    "landscape",
    "journey",
    "unlock",
    "harness",
    "embark",
    "illuminate",
    "tapestry",
    "realm",
    "passionate",
    "fast-paced",
    "results-driven",
    "synergy",
    "ultimately",
    "indeed",
    # extra clichés mandated by Phase 10.5
    "team player",
    "results-oriented",
    "results oriented",
    "go-getter",
    "go getter",
    "hit the ground running",
    "game changer",
    "think outside the box",
    "self-starter",
)

# AI-disclosure patterns: target the *claim that the message was AI-written*,
# not a candidate legitimately describing AI/ML work.
_AI_DISCLOSURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(escrit|generad|redactad|asistid|cread)\w*\s+(por|con|mediante)\s+"
        r"(una?\s+|un\s+)?(ia\b|ai\b|inteligencia artificial|sistema|agente|asistente)",
        re.IGNORECASE,
    ),
    re.compile(
        r"con\s+(la\s+)?ayuda\s+de\s+(una?\s+)?(ia\b|ai\b|inteligencia artificial)", re.IGNORECASE
    ),
    re.compile(r"\b(agente|sistema|asistente)\s+de\s+(ia|ai)\b", re.IGNORECASE),
    re.compile(r"\bgenerado\s+autom[aá]ticamente\b", re.IGNORECASE),
)


def _fold(text: str) -> str:
    """Lowercase and strip accents for accent-insensitive matching."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


_PROHIBITED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (raw, re.compile(rf"\b{re.escape(_fold(raw))}\b")) for raw in _PROHIBITED_RAW
)

_PROHIBITED_EN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (raw, re.compile(rf"\b{re.escape(_fold(raw))}\b")) for raw in _PROHIBITED_EN_RAW
)

# English AI-disclosure patterns (the patterns above are Spanish).
_AI_DISCLOSURE_EN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(written|generated|drafted|created|composed|produced)\s+(by|with|using)\s+"
        r"(an?\s+)?(ai\b|a\.i\.|artificial intelligence|llm|bot|chatbot|assistant|agent|"
        r"language model)",
        re.IGNORECASE,
    ),
    re.compile(
        r"with\s+the\s+(help|assistance)\s+of\s+(an?\s+)?(ai\b|artificial intelligence)",
        re.IGNORECASE,
    ),
    re.compile(r"\bai[-\s]generated\b", re.IGNORECASE),
)


def body_hash(text: str) -> str:
    """Return a short, stable hash of *text* for log correlation (no PII)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass
class LintResult:
    """Result of linting a draft.

    Attributes:
        ok: True when the draft passes every check.
        issues: Human-readable reasons for each failed check (empty when ok).
    """

    ok: bool
    issues: list[str] = field(default_factory=list)


def _draft_text(draft: Draft) -> str:
    """Concatenate the user-visible draft fields for text checks."""
    parts = [draft.email_subject, draft.email_body, draft.carta_presentacion or ""]
    return "\n".join(parts)


def _check_prohibited(text_folded: str) -> list[str]:
    """Return an issue per prohibited word/phrase found in the folded text.

    Matching uses word boundaries so English tells do not match inside Spanish
    words (e.g. 'realm' must not match 'realmente').
    """
    return [
        f"palabra prohibida: '{raw}'"
        for raw, pattern in _PROHIBITED_PATTERNS
        if pattern.search(text_folded)
    ]


def _check_dashes(text: str) -> list[str]:
    """Return an issue if an em-dash or en-dash is present (strictest rule)."""
    issues: list[str] = []
    if _EM_DASH in text:
        issues.append("contiene raya (em-dash); está prohibida")
    if _EN_DASH in text:
        issues.append("contiene guion largo (en-dash); está prohibido")
    return issues


def _significant_tokens(value: str) -> set[str]:
    """Return folded tokens from *value* worth matching (length >= min, non-stopword)."""
    tokens = re.findall(r"\w+", _fold(value))
    return {t for t in tokens if len(t) >= _MIN_TOKEN_LEN and t not in _NAME_STOPWORDS}


def _check_specificity(body_folded: str, dossier: CompanyDossier | None, empresa: str) -> list[str]:
    """Require the body to name the company and cite one concrete dossier fact.

    When no dossier is available the fact check cannot be verified, so only the
    company-name reference is required.
    """
    name_tokens = _significant_tokens(empresa)
    name_ok = any(tok in body_folded for tok in name_tokens) if name_tokens else False
    if not name_ok:
        return [f"el cuerpo no menciona a la empresa ('{empresa}')"]

    if dossier is None:
        return []

    fact_tokens: set[str] = set()
    for item in [*dossier.productos_o_servicios, *dossier.stack_tecnologico, dossier.ubicacion_hq]:
        fact_tokens |= _significant_tokens(item)
    # Names already satisfied; facts must be *other* tokens.
    fact_tokens -= name_tokens

    if fact_tokens and not any(tok in body_folded for tok in fact_tokens):
        return [
            "el cuerpo no cita ningún dato concreto del dossier (producto, tecnología o ubicación)"
        ]
    return []


def _check_ai_disclosure(body: str) -> list[str]:
    """Return an issue if the body discloses AI assistance."""
    for pattern in _AI_DISCLOSURE_PATTERNS:
        if pattern.search(body):
            return ["el cuerpo revela asistencia de IA"]
    return []


def lint(draft: Draft, dossier: CompanyDossier | None, empresa: str) -> LintResult:
    """Lint a generated draft against the prohibited-words and specificity rules.

    Args:
        draft: The generated draft to check.
        dossier: The company research dossier, or ``None`` if unavailable.
        empresa: The company name (``CompanyDossier`` does not carry it).

    Returns:
        A ``LintResult``. A draft already flagged ``needs_manual_context`` is
        considered ``ok`` (it is an intentional placeholder, not a failure).
    """
    if draft.needs_manual_context:
        return LintResult(ok=True)

    text = _draft_text(draft)
    text_folded = _fold(text)

    issues: list[str] = []
    issues += _check_prohibited(text_folded)
    issues += _check_dashes(text)
    issues += _check_specificity(_fold(draft.email_body), dossier, empresa)
    issues += _check_ai_disclosure(draft.email_body)

    result = LintResult(ok=not issues, issues=issues)
    logger.info(
        "draft_lint",
        ok=result.ok,
        issues=result.issues,
        body_hash=body_hash(draft.email_body),
    )
    return result


def lint_cover_letter(
    draft: CoverLetterDraft,
    *,
    dossier: CompanyDossier | None,
    empresa: str,
    language: Literal["es", "en"],
) -> LintResult:
    """Lint a Phase 10.5 ``CoverLetterDraft`` (language-aware).

    Reuses the v1 dash, specificity, and AI-disclosure checks, and selects the
    prohibited-words list by language: the combined list for Spanish drafts, the
    English banned-cliché list for English drafts. The AI-disclosure check runs
    both languages' patterns so a disclosure in either language is caught.

    Args:
        draft: The generated cover-letter draft.
        dossier: Company research dossier, or ``None`` if unavailable.
        empresa: Company name (the specificity check needs it).
        language: Offer/draft language driving the prohibited-words list.

    Returns:
        A ``LintResult``.
    """
    text = f"{draft.subject}\n{draft.body}"
    text_folded = _fold(text)
    patterns = _PROHIBITED_EN_PATTERNS if language == "en" else _PROHIBITED_PATTERNS

    issues: list[str] = [
        f"palabra prohibida: '{raw}'" for raw, pattern in patterns if pattern.search(text_folded)
    ]
    issues += _check_dashes(text)
    issues += _check_specificity(_fold(draft.body), dossier, empresa)
    issues += _check_ai_disclosure_multilang(draft.body)

    result = LintResult(ok=not issues, issues=issues)
    logger.info(
        "draft_lint_cover_letter",
        ok=result.ok,
        issues=result.issues,
        language=language,
        body_hash=body_hash(draft.body),
    )
    return result


def _check_ai_disclosure_multilang(body: str) -> list[str]:
    """Return an issue if the body discloses AI assistance in Spanish or English."""
    for pattern in (*_AI_DISCLOSURE_PATTERNS, *_AI_DISCLOSURE_EN_PATTERNS):
        if pattern.search(body):
            return ["el cuerpo revela asistencia de IA"]
    return []
