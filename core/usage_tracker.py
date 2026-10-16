"""
Per-request usage and cost accounting (ADR-005, capacity doc §3).

Cost is a first-class metric: every LLM call and tool call records its
actual usage here, aggregated per request, exported to Prometheus
(``request_cost_usd`` histogram) and attached to the response metadata.

Pricing is a **table, not magic**: list prices per 1M tokens, overridable
via settings when contracts change. Unknown models get a conservative
default so an unmapped model can't silently report $0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# USD per 1M tokens (list prices, 2026-10). Override via settings.pricing_overrides.
DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # model -> (input_per_1m, output_per_1m)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
}
_FALLBACK_PRICE = (5.00, 15.00)  # conservative default for unknown models


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for one LLM call."""
    price_in, price_out = DEFAULT_PRICING.get(model, _FALLBACK_PRICE)
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


@dataclass
class LLMUsageEvent:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class UsageReport:
    """Aggregated usage for one request — surfaced in response metadata."""

    llm_events: list[LLMUsageEvent] = field(default_factory=list)
    tool_calls: int = 0
    web_searches: int = 0
    pages_fetched: int = 0

    # ── Aggregate views ──────────────────────────────────────────────────

    @property
    def input_tokens(self) -> int:
        return sum(e.input_tokens for e in self.llm_events)

    @property
    def output_tokens(self) -> int:
        return sum(e.output_tokens for e in self.llm_events)

    @property
    def total_cost_usd(self) -> float:
        return sum(e.cost_usd for e in self.llm_events)

    @property
    def llm_calls(self) -> int:
        return len(self.llm_events)

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_calls": self.llm_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "web_searches": self.web_searches,
            "pages_fetched": self.pages_fetched,
            "estimated_cost_usd": round(self.total_cost_usd, 6),
            "by_model": {
                f"{e.provider}/{e.model}": e.to_dict() for e in self.llm_events
            },
        }


class UsageTracker:
    """
    Request-scoped usage collector.

    One instance per request, threaded alongside ``BudgetManager``.
    Budget answers "may I proceed?"; UsageTracker answers "what did it
    cost?" — separate concerns, same flight path.
    """

    def __init__(self) -> None:
        self._report = UsageReport()

    def record_llm_call(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> LLMUsageEvent:
        event = LLMUsageEvent(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=estimate_cost_usd(model, input_tokens, output_tokens),
        )
        self._report.llm_events.append(event)

        # Prometheus export (cheap: label string concat only)
        from core.observability import LLM_TOKENS

        LLM_TOKENS.labels(provider=provider, direction="input").inc(input_tokens)
        LLM_TOKENS.labels(provider=provider, direction="output").inc(output_tokens)

        logger.debug(
            "usage.llm_call",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(event.cost_usd, 6),
        )
        return event

    def record_tool_call(self, tool_name: str) -> None:
        self._report.tool_calls += 1
        if tool_name == "web_search":
            self._report.web_searches += 1
        elif tool_name in ("scrape_webpage", "fetch_url"):
            self._report.pages_fetched += 1

    def export_cost_metric(self) -> None:
        """Publish final request cost to Prometheus (call once, at end)."""
        from core.observability import REQUEST_COST

        REQUEST_COST.observe(self._report.total_cost_usd)

    @property
    def report(self) -> UsageReport:
        return self._report

    def to_dict(self) -> dict[str, Any]:
        return self._report.to_dict()
