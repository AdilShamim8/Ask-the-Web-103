"""
Web search tool — ordered provider fallback with retry (ADR-002).

Production changes vs. the course version:
* Uses the SHARED pooled HTTP client (no per-request client churn, FM-18).
* Walks the configured provider ORDER (tavily → serpapi), not a single
  choice: one provider outage degrades result quality, not the request
  (FM-02).
* Provider failures trip the per-provider circuit breaker via
  retry-with-jitter; breakers are keyed ``search:<provider>`` and shared
  per process.
* Results are normalized (title/url/snippet/score) so downstream code
  never learns which vendor answered.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from configs.settings import SearchProvider, get_settings
from core.exceptions import SearchError
from core.resilience import BreakerRegistry, retry_with_jitter
from tools.base_tool import BaseTool, ToolDefinition
from tools.http_client import get_http_client

logger = structlog.get_logger(__name__)

_breakers = BreakerRegistry()

# Transient transport failures worth one bounded retry inside the breaker
_TRANSIENT = (TimeoutError, ConnectionError)


class WebSearchTool(BaseTool):
    """Search the web via the configured provider chain."""

    timeout_s = 15.0
    cost_hint = "moderate"

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
        num_results = max(1, min(10, num_results))  # clamp, don't trust
        logger.info("web_search.query", query=query[:100], num_results=num_results)

        providers = self._settings.search_provider_order
        last_error: Exception | None = None

        for provider in providers:
            try:
                breaker = _breakers.get_or_create(f"search:{provider.value}")

                async def _do_search() -> list[dict[str, str]]:
                    if provider == SearchProvider.TAVILY:
                        return await self._tavily_search(
                            query, num_results, search_depth
                        )
                    return await self._serpapi_search(query, num_results)

                results = await breaker.call(
                    lambda: retry_with_jitter(
                        _do_search, attempts=3, base_delay_s=0.4,
                        max_delay_s=4.0, retry_on=_TRANSIENT,
                    )
                )

                if not results:
                    return json.dumps(
                        {"results": [], "query": query,
                         "message": "No results found."}
                    )
                return json.dumps(
                    {"results": results, "query": query,
                     "provider": provider.value},
                    indent=2,
                )

            except Exception as exc:
                logger.warning(
                    "web_search.provider_failed",
                    provider=provider.value,
                    error=str(exc)[:200],
                )
                last_error = exc
                continue

        raise SearchError(
            f"All search providers failed: {last_error}"
        )

    # ── Providers (normalized output shape) ──────────────────────────

    async def _tavily_search(
        self, query: str, num_results: int, search_depth: str
    ) -> list[dict[str, str]]:
        api_key = self._settings.tavily_api_key.get_secret_value()
        client = get_http_client()

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
            timeout=self._settings.search_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("content") or "")[:500],
                "score": str(r.get("score", 0)),
            }
            for r in data.get("results", [])
        ]

    async def _serpapi_search(
        self, query: str, num_results: int
    ) -> list[dict[str, str]]:
        api_key = self._settings.serpapi_api_key.get_secret_value()
        client = get_http_client()

        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "api_key": api_key,
                "q": query,
                "num": num_results,
                "engine": "google",
            },
            timeout=self._settings.search_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": (r.get("snippet") or "")[:500],
                "score": "1.0",
            }
            for r in data.get("organic_results", [])
        ]
