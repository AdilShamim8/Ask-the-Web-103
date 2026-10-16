"""
Routing Workflow — classify queries, dispatch to the right strategy.

Production hardening:
* LLM classification results are CACHED per normalized query (10 min TTL,
  in-process). Routing decisions are stable — paying the LLM twice for
  the same query is pure waste, and at scale it is meaningful money
  (capacity doc §2: routing is 1 call × every uncached question).
* Classification runs on the FAST model tier.
* Parse failures default to ``simple_qa`` — the cheapest safe strategy —
  never to a crash (degrade, don't die).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)

RouteHandler = Callable[[str, Any], Awaitable[Any]]

# Normalization for cache keys: lowercase, collapse whitespace.
_WS_RE = re.compile(r"\s+")
_ROUTE_CACHE_TTL_S = 600.0
_ROUTE_CACHE_MAX = 5_000  # bounded — a pod-local cache must not grow forever


@dataclass
class Route:
    name: str
    description: str
    handler: RouteHandler


_ROUTING_PROMPT = """\
You are a query router. Given a user query, select the best processing strategy.

Available strategies:
{routes_description}

Query: {query}

Respond with a JSON object:
{{"route": "<strategy_name>", "reason": "<one-line reason>"}}

Only output valid JSON.
"""


class QueryRouter:
    """
    Routing Workflow.

    The LLM examines the query and routes it to the most appropriate
    handler:
        - "simple_qa"      → Single-pass ReACT (short factual questions)
        - "research"       → Reflexion agent (complex research questions)
        - "multi_faceted"  → Orchestrator (multi-part questions)
        - "calculation"    → Direct calculator + brief search
        - "conversational" → Direct LLM response (no search needed)
    """

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model
        self._routes: dict[str, Route] = {}
        self._classify_cache: dict[str, tuple[str, float]] = {}

    def add_route(self, route: Route) -> QueryRouter:
        self._routes[route.name] = route
        return self

    async def route(self, query: str, context: Any = None) -> tuple[str, Any]:
        """Classify the query and dispatch. Returns (route_name, result)."""
        route_name = await self._classify(query)
        logger.info("query_router.routed", query=query[:60], route=route_name)

        if route_name not in self._routes:
            logger.warning("router.unknown_route", route=route_name)
            route_name = next(iter(self._routes))

        handler = self._routes[route_name].handler
        result = await handler(query, context)
        return route_name, result

    async def _classify(self, query: str) -> str:
        # ── Cache lookup ─────────────────────────────────────────────
        key = _WS_RE.sub(" ", query.lower().strip())
        now = time.monotonic()
        cached = self._classify_cache.get(key)
        if cached and now - cached[1] < _ROUTE_CACHE_TTL_S:
            return cached[0]

        # ── LLM classification (fast tier) ──────────────────────────
        routes_desc = "\n".join(
            f"- {r.name}: {r.description}" for r in self._routes.values()
        )
        prompt = _ROUTING_PROMPT.format(
            routes_description=routes_desc, query=query
        )

        response = await self._llm.complete(
            messages=[Message(role=Role.USER, content=prompt)],
            model=self._model,
            temperature=0.0,
            max_tokens=128,
            fast=True,
        )

        text = (response.content or "").strip()
        route_name = "simple_qa"
        try:
            if text.startswith("```"):
                text = text.split("```")[1].lstrip("json").strip()
            data = json.loads(text)
            route_name = data.get("route", "simple_qa")
        except (json.JSONDecodeError, KeyError):
            logger.warning("router.parse_failed", raw=text[:100])

        # ── Cache store (bounded) ────────────────────────────────────
        if len(self._classify_cache) >= _ROUTE_CACHE_MAX:
            # Drop the oldest ~10% — cheap amortized eviction.
            for old_key, _ in sorted(
                self._classify_cache.items(), key=lambda kv: kv[1][1]
            )[: _ROUTE_CACHE_MAX // 10]:
                self._classify_cache.pop(old_key, None)
        self._classify_cache[key] = (route_name, now)

        return route_name


class QueryClassifier:
    """
    Lightweight rule-based classifier — free pre-filter before LLM routing.
    """

    CALCULATION_KEYWORDS = frozenset([
        "calculate", "compute", "how much", "percentage", "convert",
        "what is", "equals", "formula", "math", "integral", "derivative",
    ])

    CONVERSATIONAL_KEYWORDS = frozenset([
        "hello", "hi", "thanks", "thank you", "bye", "how are you",
        "what can you do", "help me understand",
    ])

    @classmethod
    def quick_classify(cls, query: str) -> str | None:
        """Returns a route name if obvious, else None (→ LLM routing)."""
        q = query.lower().strip()

        if any(kw in q for kw in cls.CONVERSATIONAL_KEYWORDS) and len(q) < 60:
            return "conversational"

        if any(kw in q for kw in cls.CALCULATION_KEYWORDS) and len(q) < 80:
            if not any(w in q for w in ["news", "latest", "current", "who", "where"]):
                return "calculation"

        return None
