"""
Tool registry — name-indexed, append-only after startup, health-aware.

Concurrency rules (FMEA FM-13): registration happens at startup (single
task); execution is read-only over the dict. asyncio tasks on one loop
make this safe without locks; if we ever move to thread-based workers,
swap the dict for a lock-guarded copy — noted in ADR-001.
"""

from __future__ import annotations

from typing import Any

import structlog

from core.exceptions import ToolNotFoundError
from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._frozen = False

    def register(self, tool: BaseTool) -> None:
        if self._frozen:
            raise RuntimeError(
                "Registry is frozen (post-startup). Registration is a "
                "boot-time operation — see ADR-001 dependency rules."
            )
        name = tool.name
        if name in self._tools:
            logger.warning("tool.duplicate_register", tool_name=name)
            self._tools[name] = tool
            return
        self._tools[name] = tool
        logger.debug("tool.registered", tool_name=tool.name, cost_hint=tool.cost_hint)

    def freeze(self) -> None:
        """Mark registry read-only — call after MCP discovery at startup."""
        self._frozen = True
        logger.info("tool.registry_frozen", size=len(self._tools))

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def get_schemas(self) -> list[dict[str, Any]]:
        """OpenAI-format tool schemas for all registered tools."""
        return [t.definition.to_openai_format() for t in self._tools.values()]

    def get_definitions(self) -> list[ToolDefinition]:
        return [t.definition for t in self._tools.values()]

    async def health(self) -> dict[str, bool]:
        """Per-tool health — surfaced by /readyz so a dead MCP server
        degrades one tool, not the whole pod."""
        results: dict[str, bool] = {}
        for name, tool in self._tools.items():
            try:
                results[name] = await tool.health_check()
            except Exception:
                results[name] = False
        return results

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
