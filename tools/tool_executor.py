"""
Tool executor — the ONLY place tools run.

Guards applied to every call (defense in depth — each one also exists at
the tool level, but this is the enforcement point that cannot be bypassed):

1. Argument validation  → LLM output is untrusted (ToolValidationError)
2. Budget check         → consume_tool_call() before execution (ADR-005)
3. SSRF re-check        → for tools that fetch URLs (FM-08)
4. Per-call timeout     → asyncio.wait_for, tool-defined (FM-11)
5. Result truncation    → hard char cap before context injection (FM-09)
6. Metrics + usage      → TOOL_CALLS/TOOL_LATENCY, UsageTracker
7. Error normalization  → never propagates raw exceptions into agent state

Parallel execution is bounded by a semaphore — unbounded gather over
N tool calls is how scrapes exhaust connections at scale.
"""

from __future__ import annotations

import asyncio
import json
import time

import structlog

from core.budgets import BudgetManager
from core.exceptions import (
    BudgetExceededError,
    ToolExecutionError,
    ToolValidationError,
)
from core.message_types import ToolCall, ToolResult
from core.observability import TOOL_CALLS, TOOL_LATENCY
from core.usage_tracker import UsageTracker
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)


class ToolExecutor:
    """Executes tool calls with centralized enforcement and telemetry."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        budget: BudgetManager | None = None,
        usage: UsageTracker | None = None,
        max_parallel: int = 5,
    ) -> None:
        self._registry = registry
        self._budget = budget
        self._usage = usage
        self._semaphore = asyncio.Semaphore(max_parallel)

    async def execute_one(
        self,
        tool_call: ToolCall,
        *,
        budget: BudgetManager | None = None,
        usage: UsageTracker | None = None,
    ) -> ToolResult:
        budget = budget or self._budget
        usage = usage or self._usage

        log = logger.bind(tool=tool_call.name, call_id=tool_call.id)
        start = time.perf_counter()

        # ── 1. Resolve + validate arguments ──────────────────────────
        try:
            tool = self._registry.get(tool_call.name)
            arguments = tool.validate_arguments(tool_call.arguments)
        except ToolValidationError as exc:
            TOOL_CALLS.labels(tool=tool_call.name, outcome="validation_error").inc()
            log.warning("tool.invalid_args", error=str(exc))
            return self._error_result(tool_call, str(exc), start)

        except Exception as exc:
            TOOL_CALLS.labels(tool=tool_call.name, outcome="not_found").inc()
            log.warning("tool.not_found", error=str(exc))
            return self._error_result(tool_call, str(exc), start)

        # ── 2. Budget: one tool call ─────────────────────────────────
        if budget is not None:
            try:
                budget.consume_tool_call()
            except BudgetExceededError:
                TOOL_CALLS.labels(tool=tool_call.name, outcome="budget_blocked").inc()
                return self._error_result(
                    tool_call, "Tool call blocked: request budget exhausted", start
                )

        # ── 3. SSRF re-check for URL-carrying calls (belt+braces) ────
        url_arg = arguments.get("url")
        if isinstance(url_arg, str) and url_arg.startswith(("http://", "https://")):
            from tools.ssrf_guard import validate_url

            check = validate_url(url_arg)
            if not check.ok:
                TOOL_CALLS.labels(tool=tool_call.name, outcome="ssrf_blocked").inc()
                log.warning("tool.ssrf_blocked", url=url_arg[:100], reason=check.reason)
                return self._error_result(
                    tool_call, f"URL blocked by SSRF guard: {check.reason}", start
                )

        # ── 4+5. Execute under timeout, semaphore, truncation ────────
        log.info("tool.execute.start")
        try:
            async with self._semaphore:
                raw = await asyncio.wait_for(
                    tool.execute(**arguments),
                    timeout=tool.timeout_s,
                )
        except TimeoutError:
            TOOL_CALLS.labels(tool=tool_call.name, outcome="timeout").inc()
            log.warning("tool.timeout", timeout_s=tool.timeout_s)
            result = self._error_result(
                tool_call,
                f"Tool timed out after {tool.timeout_s}s",
                start,
            )
            result.is_error = True
            return result
        except ToolExecutionError as exc:
            TOOL_CALLS.labels(tool=tool_call.name, outcome="error").inc()
            log.error("tool.execute.failed", error=str(exc)[:200])
            return self._error_result(tool_call, str(exc), start)
        except Exception as exc:  # normalize unexpected tool bugs
            TOOL_CALLS.labels(tool=tool_call.name, outcome="error").inc()
            log.error("tool.execute.crashed", error=str(exc)[:200])
            return self._error_result(
                tool_call, f"Tool crashed: {type(exc).__name__}", start
            )

        elapsed = time.perf_counter() - start
        TOOL_CALLS.labels(tool=tool_call.name, outcome="ok").inc()
        TOOL_LATENCY.labels(tool=tool_call.name).observe(elapsed)
        if usage is not None:
            usage.record_tool_call(tool_call.name)

        # Truncation with a marker the LLM can understand
        from configs.settings import get_settings

        max_chars = get_settings().max_tool_result_chars
        truncated = len(raw) > max_chars
        content = raw[:max_chars]
        if truncated:
            TOOL_CALLS.labels(tool=tool_call.name, outcome="truncated").inc()
            content += f"\n...[result truncated at {max_chars} chars]"

        log.info("tool.execute.success", elapsed_s=round(elapsed, 3),
                 truncated=truncated, result_chars=len(content))

        return ToolResult(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            content=content,
            is_error=False,
            elapsed_s=round(elapsed, 3),
            truncated=truncated,
        )

    async def execute_parallel(
        self,
        tool_calls: list[ToolCall],
        *,
        budget: BudgetManager | None = None,
        usage: UsageTracker | None = None,
    ) -> list[ToolResult]:
        """
        Execute independent tool calls concurrently (bounded).

        ``return_exceptions`` is intentionally NOT used: execute_one
        already converts every failure into an error ToolResult, so
        gather can never raise — one bad tool never kills its siblings.
        """
        tasks = [
            self.execute_one(tc, budget=budget, usage=usage) for tc in tool_calls
        ]
        return list(await asyncio.gather(*tasks))

    async def execute_sequential(
        self,
        tool_calls: list[ToolCall],
        *,
        budget: BudgetManager | None = None,
        usage: UsageTracker | None = None,
    ) -> list[ToolResult]:
        results = []
        for tc in tool_calls:
            results.append(await self.execute_one(tc, budget=budget, usage=usage))
        return results

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _error_result(tool_call: ToolCall, message: str, start: float) -> ToolResult:
        return ToolResult(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            content=json.dumps({"error": message[:512]}),
            is_error=True,
            elapsed_s=round(time.perf_counter() - start, 3),
        )
