from __future__ import annotations

from typing import Any

import structlog

from core.exceptions import ToolNotFoundError
from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """
    Central registry for all available tools.
    Provides schema export for LLM tool calling.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.debug("tool.registered", tool_name=tool.name)

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool schemas for all registered tools."""
        return [t.definition.to_openai_format() for t in self._tools.values()]

    def get_definitions(self) -> list[ToolDefinition]:
        return [t.definition for t in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)