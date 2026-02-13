"""Tool catalog for agentic research agents.

Each search tool wraps a SerperService method, formatting results into text
the model can reason over. Agents pick a subset of tools from TOOL_CATALOG.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable

from maviriq.services.search import SearchResult, SerperService

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_CALL = 15


def _format_results(results: list[SearchResult]) -> str:
    """Format search results into readable text for the model."""
    if not results:
        return "No results found."
    lines: list[str] = []
    for r in results[:MAX_RESULTS_PER_CALL]:
        lines.append(f"[{r.source}] {r.title}\n{r.url}\n{r.snippet}")
    return "\n\n".join(lines)


# (tool_name, description, serper_method_name)
TOOL_CATALOG: list[tuple[str, str, str]] = [
    (
        "search_web",
        "Search Google for general web results. Use for broad queries about a topic.",
        "search",
    ),
    (
        "search_reddit",
        "Search Reddit for community discussions, complaints, and user experiences.",
        "search_reddit",
    ),
    (
        "search_hackernews",
        "Search Hacker News for technical discussions and startup commentary.",
        "search_hackernews",
    ),
    (
        "search_g2",
        "Search G2 for software reviews, ratings, and comparisons.",
        "search_g2",
    ),
    (
        "search_capterra",
        "Search Capterra for software reviews and comparisons.",
        "search_capterra",
    ),
    (
        "search_twitter",
        "Search Twitter/X for real-time opinions, complaints, and trends.",
        "search_twitter",
    ),
    (
        "search_producthunt",
        "Search Product Hunt for product launches and maker discussions.",
        "search_producthunt",
    ),
    (
        "search_linkedin_jobs",
        "Search LinkedIn Jobs to gauge hiring activity and demand signals.",
        "search_linkedin_jobs",
    ),
    (
        "search_indiehackers",
        "Search Indie Hackers for founder stories, product launches, revenue reports, and startup discussions.",
        "search_indiehackers",
    ),
    (
        "search_crunchbase",
        "Search Crunchbase for startup funding, company info, and market data.",
        "search_crunchbase",
    ),
    (
        "search_youtube",
        "Search YouTube for video reviews, tutorials, and product demos.",
        "search_youtube",
    ),
    (
        "search_news",
        "Search Google News for recent news articles and press coverage.",
        "search_news",
    ),
]

# Lookup for quick access
_CATALOG_MAP: dict[str, tuple[str, str]] = {
    name: (desc, method) for name, desc, method in TOOL_CATALOG
}


def build_tools_for_agent(
    search: SerperService,
    tool_names: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Callable[[str], Awaitable[str]]]]:
    """Build tool schemas and executor functions for an agent's tool set.

    Returns:
        (schemas, executors) where schemas is a list of dicts suitable for
        ``model.bind_tools(schemas)`` and executors maps tool name to an
        async callable that accepts a query string and returns formatted text.
    """
    schemas: list[dict[str, Any]] = []
    executors: dict[str, Callable[[str], Awaitable[str]]] = {}

    for name in tool_names:
        if name not in _CATALOG_MAP:
            raise ValueError(f"Unknown tool: {name}")
        desc, method_name = _CATALOG_MAP[name]
        search_method = getattr(search, method_name)

        schemas.append({
            "name": name,
            "description": desc,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to run.",
                    }
                },
                "required": ["query"],
            },
        })

        # Create executor closure — capture search_method by value
        def _make_executor(fn: Callable) -> Callable[[str], Awaitable[str]]:
            async def executor(query: str) -> str:
                results = await fn(query)
                return _format_results(results)
            return executor

        executors[name] = _make_executor(search_method)

    return schemas, executors
