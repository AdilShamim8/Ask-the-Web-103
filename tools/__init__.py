from __future__ import annotations

from tools.calculator import CalculatorTool
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry
from tools.web_scraper import WebScraperTool
from tools.web_search import WebSearchTool
from tools.summarizer import TextSummarizerTool


def build_default_registry() -> ToolRegistry:
    """
    Factory: creates and returns a ToolRegistry
    pre-loaded with all production tools.
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