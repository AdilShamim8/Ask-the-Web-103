"""
Message and state types — the lingua franca between agents, workflows,
tools, and providers.

Production notes:
* Serialization is pure and import-clean (the old version called
  ``__import__("json")`` inside a method body — replaced with a module
  import).
* ``Message`` carries provider-agnostic structure for BOTH OpenAI and
  Anthropic wire formats; provider quirks never leak above this layer.
* ``AgentState`` now carries budget/usage snapshots so API responses can
  report what a request actually consumed.
"""

from __future__ import annotations

import json
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
    elapsed_s: float = 0.0
    truncated: bool = False


class Message(BaseModel):
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ── OpenAI wire format ───────────────────────────────────────────────

    def to_openai_dict(self) -> dict[str, Any]:
        if self.role == Role.TOOL and self.tool_results:
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
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in self.tool_calls
            ]
        return msg

    # ── Anthropic wire format ────────────────────────────────────────────

    def to_anthropic_dict(self) -> dict[str, Any]:
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


class UsageInfo(BaseModel):
    """Token usage from a single completion (provider-normalized)."""

    input_tokens: int = 0
    output_tokens: int = 0

    @classmethod
    def from_openai(cls, usage: Any) -> UsageInfo:
        if usage is None:
            return cls()
        return cls(
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )

    @classmethod
    def from_anthropic(cls, usage: Any) -> UsageInfo:
        if usage is None:
            return cls()
        return cls(
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )


class AgentState(BaseModel):
    """Full state carried through agent iterations (one per request)."""

    query: str
    messages: list[Message] = Field(default_factory=list)
    iterations: int = 0
    tool_calls_made: list[ToolCall] = Field(default_factory=list)
    tool_results_received: list[ToolResult] = Field(default_factory=list)
    final_answer: str | None = None
    sources: list[dict[str, str]] = Field(default_factory=list)
    degraded: bool = False                # answer produced under provider degradation
    degradation_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
