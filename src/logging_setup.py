"""Structured logging configuration using structlog with PII masking."""

import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

# Patterns for PII masking
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Spanish phone formats: +34 6XX/7XX/9XX XXXXXXX, national 6XX XXX XXX, etc.
_PHONE_RE = re.compile(r"(?:\+34[\s.-]?)?(?:6|7|9)\d{2}[\s.-]?\d{3}[\s.-]?\d{3}")


def _mask_pii(value: str) -> str:
    """Replace emails and phone numbers in *value* with placeholder tokens."""
    value = _EMAIL_RE.sub("[EMAIL]", value)
    value = _PHONE_RE.sub("[PHONE]", value)
    return value


def _pii_masking_processor(logger: WrappedLogger, method: str, event_dict: EventDict) -> EventDict:
    """Structlog processor that masks PII in all string values of the event dict."""
    for key, val in event_dict.items():
        if isinstance(val, str):
            event_dict[key] = _mask_pii(val)
    return event_dict


def configure_logging(json_logs: bool = False) -> None:
    """Configure structlog for the application.

    Args:
        json_logs: When True emit newline-delimited JSON (suitable for CI/log
            aggregators). When False use a human-friendly coloured renderer.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _pii_masking_processor,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
