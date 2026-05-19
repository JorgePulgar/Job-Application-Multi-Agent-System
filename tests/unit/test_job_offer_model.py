"""Unit tests for the JobOffer Pydantic model."""

from __future__ import annotations

import datetime

import pytest

from src.models.job_offer import JobOffer, Modalidad, _normalize

# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("ML Engineer", "ml engineer"),
        ("Málaga", "malaga"),  # accent stripped via NFKD
        ("  hello   world  ", "hello world"),  # whitespace collapsed
        ("hello, world!", "hello world"),  # punctuation stripped
        ("Ñoño", "nono"),  # ñ -> n via NFKD
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert _normalize(raw) == expected


# ---------------------------------------------------------------------------
# hash_unico — deduplication
# ---------------------------------------------------------------------------


def _offer(**kwargs: object) -> JobOffer:
    base: dict[str, object] = {
        "titulo": "ML Engineer",
        "empresa": "Acme SL",
        "ubicacion": "Madrid",
        "plataforma": "adzuna",
    }
    base.update(kwargs)
    return JobOffer.model_validate(base)


def test_hash_unico_identical_offers() -> None:
    a = _offer()
    b = _offer()
    assert a.hash_unico == b.hash_unico


def test_hash_unico_case_insensitive() -> None:
    a = _offer(titulo="ML Engineer", empresa="Acme SL", ubicacion="Madrid")
    b = _offer(titulo="ml engineer", empresa="ACME SL", ubicacion="MADRID")
    assert a.hash_unico == b.hash_unico


def test_hash_unico_accent_insensitive() -> None:
    a = _offer(ubicacion="Málaga")
    b = _offer(ubicacion="Malaga")
    assert a.hash_unico == b.hash_unico


def test_hash_unico_different_offers() -> None:
    a = _offer(titulo="ML Engineer")
    b = _offer(titulo="Data Engineer")
    assert a.hash_unico != b.hash_unico


def test_hash_unico_is_64_hex_chars() -> None:
    o = _offer()
    assert len(o.hash_unico) == 64
    assert all(c in "0123456789abcdef" for c in o.hash_unico)


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def test_defaults() -> None:
    o = _offer()
    assert o.modalidad == Modalidad.unknown
    assert o.salario_min is None
    assert o.salario_max is None
    assert o.fecha_publicacion is None


def test_optional_salary() -> None:
    o = _offer(salario_min=40000, salario_max=60000)
    assert o.salario_min == 40000
    assert o.salario_max == 60000


def test_fecha_publicacion_parsed() -> None:
    o = _offer(fecha_publicacion="2026-01-15")
    assert o.fecha_publicacion == datetime.date(2026, 1, 15)


# ---------------------------------------------------------------------------
# to_db_offer
# ---------------------------------------------------------------------------


def test_to_db_offer_columns() -> None:
    o = _offer(
        titulo="ML Engineer",
        empresa="Acme SL",
        ubicacion="Madrid",
        descripcion="Great role.",
        url="https://example.com/job/1",
        salario_min=50000,
    )
    db_row = o.to_db_offer(user_id=1, company_id=None)
    assert db_row.titulo == "ML Engineer"
    assert db_row.empresa == "Acme SL"
    assert db_row.ubicacion == "Madrid"
    assert db_row.descripcion == "Great role."
    assert db_row.url == "https://example.com/job/1"
    assert db_row.hash_unico == o.hash_unico
    assert db_row.user_id == 1
    assert db_row.company_id is None
    assert db_row.fuente == "adzuna"


def test_to_db_offer_with_company() -> None:
    o = _offer()
    db_row = o.to_db_offer(user_id=2, company_id=7)
    assert db_row.company_id == 7


def test_to_db_offer_with_fecha_publicacion() -> None:
    o = _offer(fecha_publicacion="2026-03-10")
    db_row = o.to_db_offer(user_id=1)
    assert db_row.fecha_publicacion is not None
    assert db_row.fecha_publicacion.date() == datetime.date(2026, 3, 10)
