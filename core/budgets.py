"""
Request budgets — the anti-runaway guard (ADR-005, FMEA FM-06/FM-07).

Every request creates one ``BudgetManager`` which is threaded through the
agent → workflow → tool stack. Before any billable action, actors call a
``consume_*`` method. Exhausting any dimension raises ``BudgetExceededError``
which the API layer maps to HTTP 422 (with a best-effort partial answer).

Why four dimensions and not just max_iterations:
    tokens  → cost control (an iteration can be $0.001 or $0.50)
    tools   → external spend (search APIs bill per call; scrapes cost egress)
    steps   → loop termination independent of cost
    deadline→ latency control (the user will not wait 90s regardless of spend)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

from core.exceptions import BudgetExceededError

logger = structlog.get_logger(__name__)


@dataclass
class BudgetConfig:
    """Limits for a single request. Defaults come from configs/settings.py."""

    max_input_tokens: int = 120_000
    max_output_tokens: int = 16_000
    max_tool_calls: int = 25
    max_steps: int = 12
    deadline_s: float = 45.0

    @classmethod
    def from_settings(cls) -> BudgetConfig:
        """Build from application settings, so ops can tune via env vars."""
        from configs.settings import get_settings

        s = get_settings()
        return cls(
            max_input_tokens=s.budget_max_input_tokens,
            max_output_tokens=s.budget_max_output_tokens,
            max_tool_calls=s.budget_max_tool_calls,
            max_steps=s.budget_max_steps,
            deadline_s=s.budget_deadline_s,
        )


@dataclass
class BudgetSnapshot:
    """Point-in-time budget state — attached to AgentState.metadata."""

    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    steps: int = 0
    elapsed_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "steps": self.steps,
            "elapsed_s": round(self.elapsed_s, 2),
        }


class BudgetManager:
    """
    Mutable, request-scoped budget tracker.

    Not thread-safe by design: one asyncio task tree per request, and all
    mutations happen on the event loop. For parallel workers, children get
    ``fork()`` views sharing the same counters (orchestrator fan-out must
    collectively respect the parent budget).
    """

    def __init__(self, config: BudgetConfig | None = None) -> None:
        self._config = config or BudgetConfig()
        self._start = time.monotonic()
        self.input_tokens = 0
        self.output_tokens = 0
        self.tool_calls = 0
        self.steps = 0

    # ── Consuming budget ─────────────────────────────────────────────────

    def consume_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Record estimated/actual token usage; raise if over budget."""
        if self.input_tokens + input_tokens > self._config.max_input_tokens:
            self._raise("input_tokens", self._config.max_input_tokens,
                        self.input_tokens + input_tokens)
        if self.output_tokens + output_tokens > self._config.max_output_tokens:
            self._raise("output_tokens", self._config.max_output_tokens,
                        self.output_tokens + output_tokens)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def reserve_output(self, output_tokens: int) -> None:
        """Pre-check (before an LLM call) that the response will fit budget."""
        if self.output_tokens + output_tokens > self._config.max_output_tokens:
            self._raise("output_tokens", self._config.max_output_tokens,
                        self.output_tokens + output_tokens)

    def consume_tool_call(self) -> None:
        if self.tool_calls + 1 > self._config.max_tool_calls:
            self._raise("tool_calls", self._config.max_tool_calls, self.tool_calls + 1)
        self.tool_calls += 1

    def consume_step(self) -> None:
        if self.steps + 1 > self._config.max_steps:
            self._raise("steps", self._config.max_steps, self.steps + 1)
        self.steps += 1

    def check_deadline(self) -> None:
        """Raise if wall-clock budget is exhausted (check before each step)."""
        elapsed = time.monotonic() - self._start
        if elapsed > self._config.deadline_s:
            self._raise("deadline_s", self._config.deadline_s, round(elapsed, 2))

    # ── Introspection ────────────────────────────────────────────────────

    def time_remaining_s(self) -> float:
        return max(0.0, self._config.deadline_s - (time.monotonic() - self._start))

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            tool_calls=self.tool_calls,
            steps=self.steps,
            elapsed_s=time.monotonic() - self._start,
        )

    def would_exceed(self, input_tokens: int = 0, tool_calls: int = 0) -> bool:
        """Non-raising check for planners deciding whether to start work."""
        return (
            self.input_tokens + input_tokens > self._config.max_input_tokens
            or self.tool_calls + tool_calls > self._config.max_tool_calls
            or self.time_remaining_s() <= 0
        )

    # ── Internal ─────────────────────────────────────────────────────────

    def _raise(self, dimension: str, limit: int | float, consumed: int | float) -> None:
        logger.warning(
            "budget.exceeded",
            dimension=dimension,
            limit=limit,
            consumed=consumed,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            tool_calls=self.tool_calls,
            steps=self.steps,
        )
        raise BudgetExceededError(dimension=dimension, limit=limit, consumed=consumed)
