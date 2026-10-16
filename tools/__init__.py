"""
Tools package — registry, executor, and the default production toolset.

build_default_registry() is the composition root for tools. MCP servers
are attached at app startup (api/main.py lifespan) so a hung external
server never blocks imports.
"""

from __future__ import annotations

from tools.calculator import CalculatorTool
from tools.summarizer import TextSummarizerTool
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry
from tools.web_scraper import WebScraperTool
from tools.web_search import WebSearchTool


def build_default_registry() -> ToolRegistry:
    """
    Factory: ToolRegistry pre-loaded with built-in production tools.

    Note: registry.freeze() is called by the app lifespan AFTER MCP
    discovery, so dynamically-discovered tools are merged before the
    registry becomes read-only.
    """
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(WebScraperTool())
    registry.register(CalculatorTool())
    registry.register(TextSummarizerTool())
    return registry


__all__ = [
    "ToolRegistry",
    "ToolExecutor",
    "WebSearchTool",
    "WebScraperTool",
    "CalculatorTool",
    "TextSummarizerTool",
    "build_default_registry",
]
