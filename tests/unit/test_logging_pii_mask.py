"""Unit tests for PII masking in the logging pipeline."""

import pytest

from src.logging_setup import _mask_pii


@pytest.mark.parametrize(
    "input_str, expected",
    [
        # Email addresses
        ("Contact jorge@example.com for info", "Contact [EMAIL] for info"),
        ("Send to user.name+tag@sub.domain.es today", "Send to [EMAIL] today"),
        ("no pii here", "no pii here"),
        # Spanish mobile numbers (6XX / 7XX)
        ("Llama al 612 345 678 ahora", "Llama al [PHONE] ahora"),
        ("Móvil: 722345678", "Móvil: [PHONE]"),
        ("Tel +34 699 123 456", "Tel [PHONE]"),
        ("Tel +34-699-123-456", "Tel [PHONE]"),
        # Spanish landline (9XX)
        ("Oficina: 912 345 678", "Oficina: [PHONE]"),
        # Both in same string
        (
            "Email user@test.com o llama 634 567 890",
            "Email [EMAIL] o llama [PHONE]",
        ),
        # Multiple emails
        (
            "Copia a a@b.com y c@d.es",
            "Copia a [EMAIL] y [EMAIL]",
        ),
    ],
)
def test_mask_pii(input_str: str, expected: str) -> None:
    assert _mask_pii(input_str) == expected
