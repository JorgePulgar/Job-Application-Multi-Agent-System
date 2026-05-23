"""Pydantic model for a single web search result."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single result returned by the web search service.

    Attributes:
        title: Page title as returned by the search provider.
        url: Canonical URL of the page.
        snippet: Short excerpt or description from the page.
    """

    title: str = Field(..., description="Page title.")
    url: str = Field(..., description="Page URL.")
    snippet: str = Field(..., description="Short excerpt from the page.")
