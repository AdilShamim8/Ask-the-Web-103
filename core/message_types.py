from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: f"call_{uuid4().hex[:8]}")
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    tool_call_id: str
    tool_name: str
    content: str
    is_error: bool = False


class Message(BaseModel):
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_openai_dict(self) -> dict[str, Any]:
        """Serialize to OpenAI API format."""
        if self.role == Role.TOOL and self.tool_results:
            # OpenAI expects one message per tool result
            result = self.tool_results[0]
            return {
                "role": "tool",
                "tool_call_id": result.tool_call_id,
                "content": result.content,
            }

        msg: dict[str, Any] = {"role": self.role.value}

        if self.content:
            msg["content"] = self.content

        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": __import__("json").dumps(tc.arguments),
                    },
                }
                for tc in self.tool_calls
            ]

        return msg

    def to_anthropic_dict(self) -> dict[str, Any]:
        """Serialize to Anthropic API format."""
        if self.role == Role.TOOL and self.tool_results:
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": r.tool_call_id,
                        "content": r.content,
                        "is_error": r.is_error,
                    }
                    for r in self.tool_results
                ],
            }

        msg: dict[str, Any] = {"role": self.role.value}

        if self.tool_calls:
            msg["content"] = [
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
                for tc in self.tool_calls
            ]
        else:
            msg["content"] = self.content or ""

        return msg


class AgentState(BaseModel):
    """Full mutable state carried through agent iterations."""

    query: str
    messages: list[Message] = Field(default_factory=list)
    iterations: int = 0
    tool_calls_made: list[ToolCall] = Field(default_factory=list)
    tool_results_received: list[ToolResult] = Field(default_factory=list)
    final_answer: str | None = None
    sources: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)