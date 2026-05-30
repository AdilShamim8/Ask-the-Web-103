from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from core.exceptions import ToolExecutionError, ToolNotFoundError
from core.message_types import ToolCall, ToolResult
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)


class ToolExecutor:
    """
    Executes tool calls, handles errors gracefully,
    and supports parallel execution for independent tool calls.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def execute_one(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call and return its result."""
        log = logger.bind(tool=tool_call.name, call_id=tool_call.id)
        log.info("tool.execute.start")
        start = time.perf_counter()

        try:
            tool = self._registry.get(tool_call.name)
            result_str = await tool.execute(**tool_call.arguments)
            elapsed = time.perf_counter() - start
            log.info("tool.execute.success", elapsed_s=round(elapsed, 3))
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=result_str,
                is_error=False,
            )
        except ToolNotFoundError as exc:
            log.warning("tool.not_found", error=str(exc))
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=f"ERROR: {exc}",
                is_error=True,
            )
        except Exception as exc:
            log.error("tool.execute.failed", error=str(exc))
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=f"ERROR executing '{tool_call.name}': {exc}",
                is_error=True,
            )

    async def execute_parallel(
        self, tool_calls: list[ToolCall]
    ) -> list[ToolResult]:
        """Execute multiple tool calls concurrently."""
        tasks = [self.execute_one(tc) for tc in tool_calls]
        return list(await asyncio.gather(*tasks))

    async def execute_sequential(
        self, tool_calls: list[ToolCall]
    ) -> list[ToolResult]:
        """Execute tool calls one at a time (for stateful tools)."""
        results = []
        for tc in tool_calls:
            results.append(await self.execute_one(tc))
        return results