from __future__ import annotations

import json
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from configs.settings import SearchProvider, get_settings
from core.exceptions import SearchError
from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)


class WebSearchTool(BaseTool):
    """
    Searches the web using Tavily (primary) or SerpAPI (fallback).
    Returns structured search results with titles, URLs, and snippets.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description=(
                "Search the web for current information about any topic. "
                "Returns a list of relevant web pages with titles, URLs, and snippets. "
                "Use this when you need real-time or up-to-date information."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": "Search depth: basic (fast) or advanced (deeper)",
                        "default": "basic",
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        search_depth: str = "basic",
        **_: Any,
    ) -> str:
        logger.info("web_search.query", query=query, num_results=num_results)

        try:
            if self._settings.search_provider == SearchProvider.TAVILY:
                results = await self._tavily_search(query, num_results, search_depth)
            else:
                results = await self._serpapi_search(query, num_results)

            if not results:
                return json.dumps({"results": [], "message": "No results found."})

            return json.dumps({"results": results, "query": query}, indent=2)

        except Exception as exc:
            raise SearchError(f"Web search failed: {exc}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=5),
        reraise=True,
    )
    async def _tavily_search(
        self, query: str, num_results: int, search_depth: str
    ) -> list[dict[str, str]]:
        api_key = self._settings.tavily_api_key.get_secret_value()

        async with httpx.AsyncClient(timeout=self._settings.search_timeout) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": search_depth,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:500],
                "score": str(r.get("score", 0)),
            }
            for r in data.get("results", [])
        ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=5),
        reraise=True,
    )
    async def _serpapi_search(
        self, query: str, num_results: int
    ) -> list[dict[str, str]]:
        api_key = self._settings.serpapi_api_key.get_secret_value()

        async with httpx.AsyncClient(timeout=self._settings.search_timeout) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "api_key": api_key,
                    "q": query,
                    "num": num_results,
                    "engine": "google",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", "")[:500],
                "score": "1.0",
            }
            for r in data.get("organic_results", [])
        ]