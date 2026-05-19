"""Shared HTTP client factory and robots.txt compliance helper."""

from __future__ import annotations

import contextlib
import functools
import urllib.parse
import urllib.robotparser

import httpx

_USER_AGENT = "job-agent/1.0 (automated job research; contact: admin@job-agent.local)"
_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)


def make_http_client(
    *, retries: int = 3, headers: dict[str, str] | None = None
) -> httpx.AsyncClient:
    """Return a configured ``httpx.AsyncClient`` for scraping.

    Args:
        retries: Number of transport-level retries on network errors.
        headers: Additional headers merged on top of the defaults.

    Returns:
        A ready-to-use async HTTP client. Caller is responsible for closing it
        (use as an async context manager).
    """
    base_headers = {"User-Agent": _USER_AGENT, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
    if headers:
        base_headers.update(headers)
    transport = httpx.AsyncHTTPTransport(retries=retries)
    return httpx.AsyncClient(
        headers=base_headers,
        timeout=_TIMEOUT,
        transport=transport,
        follow_redirects=True,
    )


@functools.lru_cache(maxsize=128)
def _fetch_robots(base_url: str) -> urllib.robotparser.RobotFileParser:
    """Fetch and parse robots.txt for *base_url* (cached per domain).

    Args:
        base_url: Scheme + host, e.g. ``"https://www.example.com"``.

    Returns:
        A parsed ``RobotFileParser`` instance.
    """
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(f"{base_url}/robots.txt")
    with contextlib.suppress(Exception):
        parser.read()
    return parser


def is_allowed(url: str, ua: str = _USER_AGENT) -> bool:
    """Return ``True`` if *ua* is allowed to fetch *url* per the site's robots.txt.

    Args:
        url: The full URL to check.
        ua: User-agent string to check against. Defaults to the shared UA.

    Returns:
        ``True`` when the UA is permitted or robots.txt is unreachable.
    """
    parsed = urllib.parse.urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    parser = _fetch_robots(base_url)
    return parser.can_fetch(ua, url)
