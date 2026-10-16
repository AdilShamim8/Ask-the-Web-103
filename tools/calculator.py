from __future__ import annotations

import ast
import math
import operator
from typing import Any

import structlog

from core.exceptions import ToolExecutionError
from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)

# Allowed AST node types for safe eval.
# NOTE: ast.Load / ast.Store are expression CONTEXTS that appear in every
# name reference on Python 3.12+ — they must be allowlisted or every
# function-call expression is rejected (latent bug on modern Python,
# found by the test suite 2026-10-16).
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
    ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd,
    ast.Call, ast.Name, ast.Load, ast.Store,
)

_SAFE_NAMES = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
    "log2": math.log2, "exp": math.exp, "pow": pow,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
}


def _safe_eval(expression: str) -> float:
    """
    Safely evaluate a mathematical expression.
    Only allows whitelisted functions and operators.

    Guards: length cap (DoS via pathological parse trees), AST allowlist,
    empty-builtins eval. No network, no imports, no attribute access.
    """
    expression = expression.strip()
    if not expression:
        raise ToolExecutionError("calculator", "Empty expression")
    if len(expression) > 1_000:
        raise ToolExecutionError("calculator", "Expression exceeds 1000 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolExecutionError("calculator", f"Syntax error: {exc}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ToolExecutionError(
                "calculator", f"Disallowed expression node: {type(node).__name__}"
            )
        if isinstance(node, ast.Name) and node.id not in _SAFE_NAMES:
            raise ToolExecutionError(
                "calculator", f"Unknown name: {node.id}"
            )

    try:
        result = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, _SAFE_NAMES)
        return float(result)
    except Exception as exc:
        raise ToolExecutionError("calculator", str(exc)) from exc


class CalculatorTool(BaseTool):
    """Safe mathematical expression evaluator."""

    timeout_s = 5.0
    cost_hint = "cheap"

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description=(
                "Evaluate a safe mathematical expression and return the result. "
                "Supports: +, -, *, /, **, //, %, sqrt, log, sin, cos, tan, pi, e."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "A mathematical expression to evaluate, e.g. "
                            "'sqrt(144) + 2**8' or 'sin(pi/2)'"
                        ),
                    }
                },
                "required": ["expression"],
            },
        )

    async def execute(self, expression: str, **_: Any) -> str:
        logger.debug("calculator.eval", expression=expression)
        result = _safe_eval(expression)

        # Format nicely: avoid scientific notation for normal ranges
        if result == int(result) and abs(result) < 1e15:
            return str(int(result))
        return f"{result:.10g}"