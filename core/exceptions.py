"""
Exception hierarchy for Ask-the-Web.

Design rules (production):
1. Every error carries a stable machine-readable ``error_code`` — logs,
   alerts, and clients key off codes, not strings.
2. Every error declares whether it is ``retryable`` and its ``severity`` —
   the resilience layer (core/resilience.py) retries ONLY retryable ones,
   preventing retry storms on permanent failures (FMEA FM-03).
3. Every error maps to an HTTP status via ``http_status`` — the API layer
   never invents statuses ad hoc.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorSeverity(StrEnum):
    """Operational severity — drives alerting routing."""

    INFO = "info"          # expected, no action (e.g., tool returned no results)
    WARNING = "warning"    # degraded behavior, watch it
    CRITICAL = "critical"  # user-visible failures, page someone


class AgentBaseError(Exception):
    """Base for all application errors."""

    error_code: str = "agent_internal_error"
    http_status: int = 500
    severity: ErrorSeverity = ErrorSeverity.CRITICAL
    retryable: bool = False

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context: dict = context or {}

    def to_dict(self) -> dict:
        """Structured payload for API error responses and logs."""
        return {
            "error": self.error_code,
            "detail": str(self),
            "severity": self.severity.value,
            "retryable": self.retryable,
            "context": self.context,
        }


# ── LLM / providers ──────────────────────────────────────────────────────────


class LLMError(AgentBaseError):
    """LLM call failed after retries and fallbacks."""

    error_code = "llm_error"
    http_status = 502
    severity = ErrorSeverity.CRITICAL

    def __init__(self, message: str, provider: str = "", model: str = "") -> None:
        super().__init__(message, context={"provider": provider, "model": model})
        self.provider = provider
        self.model = model


class ProviderUnavailableError(AgentBaseError):
    """All providers for a capability are down (breakers open)."""

    error_code = "provider_unavailable"
    http_status = 503
    severity = ErrorSeverity.CRITICAL
    retryable = True


class RateLimitError(AgentBaseError):
    """Upstream rate limit hit — back off, do not retry immediately."""

    error_code = "rate_limited"
    http_status = 429
    severity = ErrorSeverity.WARNING
    retryable = True


# ── Budgets (FMEA FM-06/FM-07) ───────────────────────────────────────────────


class BudgetExceededError(AgentBaseError):
    """
    Request exceeded its resource budget (tokens / tools / steps / time).

    This is a *protective* error: the request was terminated before it
    could hurt latency or cost. The API returns 422 plus a best-effort
    partial answer when available.
    """

    error_code = "budget_exceeded"
    http_status = 422
    severity = ErrorSeverity.WARNING
    retryable = False

    def __init__(self, dimension: str, limit: int | float, consumed: int | float) -> None:
        message = (
            f"Request budget exceeded on '{dimension}': "
            f"consumed {consumed}, limit {limit}."
        )
        super().__init__(
            message,
            context={"dimension": dimension, "limit": limit, "consumed": consumed},
        )
        self.dimension = dimension


# ── Tools ────────────────────────────────────────────────────────────────────


class ToolExecutionError(AgentBaseError):
    """A tool raised an error during execution."""

    error_code = "tool_execution_error"
    http_status = 500
    severity = ErrorSeverity.WARNING

    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' failed: {reason}",
            context={"tool_name": tool_name, "reason": reason},
        )
        self.tool_name = tool_name
        self.reason = reason


class ToolTimeoutError(ToolExecutionError):
    """Tool exceeded its per-call timeout — treated as non-retryable per call."""

    error_code = "tool_timeout"
    severity = ErrorSeverity.WARNING
    retryable = False


class ToolNotFoundError(AgentBaseError):
    """Tool not registered — usually an LLM hallucinating a tool name."""

    error_code = "tool_not_found"
    http_status = 400
    severity = ErrorSeverity.INFO

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool '{tool_name}' is not registered.",
            context={"tool_name": tool_name},
        )
        self.tool_name = tool_name


class ToolValidationError(AgentBaseError):
    """LLM-produced tool arguments failed schema validation."""

    error_code = "tool_validation_error"
    http_status = 400
    severity = ErrorSeverity.WARNING


class SSRFBlockedError(ToolExecutionError):
    """URL rejected by the SSRF guard (FMEA FM-08)."""

    error_code = "ssrf_blocked"
    severity = ErrorSeverity.WARNING
    retryable = False

    def __init__(self, url: str, reason: str) -> None:
        super().__init__("fetch_url", f"blocked: {reason}")
        self.context |= {"url": url, "reason": reason}


# ── Context / iterations ─────────────────────────────────────────────────────


class ContextWindowExceededError(AgentBaseError):
    """Message history exceeds the model context window."""

    error_code = "context_window_exceeded"
    http_status = 422
    severity = ErrorSeverity.WARNING


class MaxIterationsExceededError(AgentBaseError):
    """Agent exceeded max allowed iterations (legacy guard — budgets supersede)."""

    error_code = "max_iterations_exceeded"
    http_status = 422
    severity = ErrorSeverity.WARNING


# ── Web / search ─────────────────────────────────────────────────────────────


class SearchError(AgentBaseError):
    """Web search failed on all configured providers."""

    error_code = "search_error"
    http_status = 502
    severity = ErrorSeverity.WARNING
    retryable = True


class ScrapingError(AgentBaseError):
    """Web scraping failed."""

    error_code = "scraping_error"
    http_status = 502
    severity = ErrorSeverity.WARNING
    retryable = True


# ── Protocols: MCP / A2A ─────────────────────────────────────────────────────


class MCPError(AgentBaseError):
    """MCP server protocol or transport failure."""

    error_code = "mcp_error"
    http_status = 502
    severity = ErrorSeverity.WARNING
    retryable = True


class A2AError(AgentBaseError):
    """Agent-to-agent task failed, timed out, or remote agent is unhealthy."""

    error_code = "a2a_error"
    http_status = 502
    severity = ErrorSeverity.WARNING
    retryable = True


# ── Generic validation (kept for backward compatibility) ─────────────────────


class ValidationError(AgentBaseError):
    """Input/output validation failed."""

    error_code = "validation_error"
    http_status = 400
    severity = ErrorSeverity.INFO
