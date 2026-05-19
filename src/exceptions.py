"""Shared exception hierarchy for the job-agent system."""

from __future__ import annotations


class JobAgentError(RuntimeError):
    """Base class for all job-agent errors."""


class MissingCredentialsError(JobAgentError):
    """Raised when a required API credential is absent or empty."""


class ScraperError(JobAgentError):
    """Raised when a scraper encounters an unrecoverable error."""
