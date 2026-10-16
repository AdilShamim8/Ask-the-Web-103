"""
Tool contracts: definition schema + abstract base.

Production additions:
* Tools declare ``timeout_s`` and ``cost_hint`` — the executor enforces
  the timeout and the planner can weigh cost hints when choosing tools.
* ``validate_arguments`` hook: the model's JSON arguments are validated
  against the declared schema BEFORE execution (the LLM is untrusted
  input — see ARCHITECTURE.md principle 4).
"""

from __future__ import annotations

import abc
from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """JSON Schema definition used by the LLM for tool calling."""

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1, max_length=1024)
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

    Contract:
    * ``definition`` — stable name + JSON schema (what the LLM sees).
    * ``execute(**kwargs)`` — pure async function; raise
      ``ToolExecutionError`` on failure, NEVER return error text yourself
      (the executor marks is_error consistently).
    * Optional ``timeout_s`` / ``cost_hint`` class attributes tune the
      executor and planner.
    """

    # Executor kills the call after this many seconds (per-call, FM-11).
    timeout_s: float = 15.0
    # Rough per-call cost signal for planners: "cheap" | "moderate" | "expensive"
    cost_hint: str = "moderate"

    @property
    @abc.abstractmethod
    def definition(self) -> ToolDefinition:
        ...

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    @property
    def name(self) -> str:
        return self.definition.name

    # ── Argument validation ──────────────────────────────────────────────

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Validate LLM-produced arguments against the declared schema.

        Enforces ``required`` keys and rejects unknown extras, which are
        the two failure modes hallucinating models actually produce.
        Full JSON-Schema validation is overkill here; schemas in this
        codebase are deliberately simple (object with typed properties).
        """
        schema = self.definition.parameters
        if schema.get("type") != "object":
            return arguments  # non-object schemas pass through untouched

        props: dict[str, Any] = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        missing = [k for k in required if k not in arguments]
        if missing:
            from core.exceptions import ToolValidationError

            raise ToolValidationError(
                f"{self.name}: missing required argument(s): {missing}",
                context={"tool": self.name, "missing": missing},
            )

        extra = [k for k in arguments if k not in props]
        if extra and schema.get("additionalProperties") is False:
            from core.exceptions import ToolValidationError

            raise ToolValidationError(
                f"{self.name}: unexpected argument(s): {extra}",
                context={"tool": self.name, "extra": extra},
            )

        return arguments

    # ── Health (used by registry.healthy()) ──────────────────────────────

    async def health_check(self) -> bool:
        """Cheap liveness probe; override for stateful tools (MCP, pools)."""
        return True
