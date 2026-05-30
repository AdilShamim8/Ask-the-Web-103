from __future__ import annotations


class AgentBaseError(Exception):
    """Base for all agent errors."""


class LLMError(AgentBaseError):
    """LLM call failed."""

    def __init__(self, message: str, provider: str = "", model: str = "") -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model


class ToolExecutionError(AgentBaseError):
    """A tool raised an error during execution."""

    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(f"Tool '{tool_name}' failed: {reason}")
        self.tool_name = tool_name
        self.reason = reason


class ContextWindowExceededError(AgentBaseError):
    """Message history exceeds the model context window."""


class MaxIterationsExceededError(AgentBaseError):
    """Agent exceeded max allowed iterations."""


class ToolNotFoundError(AgentBaseError):
    """Tool not found in registry."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' is not registered.")
        self.tool_name = tool_name


class SearchError(AgentBaseError):
    """Web search failed."""


class ScrapingError(AgentBaseError):
    """Web scraping failed."""


class ValidationError(AgentBaseError):
    """Input/output validation failed."""