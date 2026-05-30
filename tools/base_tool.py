from __future__ import annotations

import abc
from typing import Any

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """JSON Schema definition used by the LLM for tool calling."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai_format(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseTool(abc.ABC):
    """
    Abstract base for all tools.
    Every tool must declare its schema and implement `execute`.
    """

    @property
    @abc.abstractmethod
    def definition(self) -> ToolDefinition:
        ...

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """
        Execute the tool and return a string result.
        Raise ToolExecutionError on failure.
        """
        ...

    @property
    def name(self) -> str:
        return self.definition.name