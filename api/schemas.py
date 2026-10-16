"""
API schemas — request/response contracts (v2).

Changes vs 1.0:
* Version-aware: every response carries ``api_version``.
* ``ErrorResponse`` standardized to the error-code model from
  core/exceptions.py — clients branch on codes, not strings.
* ``QueryResponse`` carries usage + budget + degradation disclosures
  (honest answers about what the request cost and whether quality was
  reduced).
* Validation tightened: query length, iteration bounds, model allowlist
  hook.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from core import __version__


class AgentTypeRequest(StrEnum):
    REACT = "react"
    REFLEXION = "reflexion"
    ORCHESTRATOR = "orchestrator"
    AUTO = "auto"  # Uses the routed pipeline


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to ask the web agent",
    )
    agent_type: AgentTypeRequest = Field(
        default=AgentTypeRequest.AUTO,
        description="Which agent strategy to use",
    )
    model: str | None = Field(
        default=None,
        description="Override the default LLM model",
    )
    max_iterations: int | None = Field(
        default=None, ge=1, le=20,
        description="Max reasoning iterations",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the final answer token-by-token",
    )
    use_cache: bool = Field(
        default=True,
        description="Serve from response cache when available (ADR-003)",
    )

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        return v.strip()


class SourceItem(BaseModel):
    title: str
    url: str


class UsageInfoResponse(BaseModel):
    """What this request consumed (cost transparency, ADR-005)."""

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    web_searches: int = 0
    pages_fetched: int = 0
    estimated_cost_usd: float = 0.0


class BudgetInfoResponse(BaseModel):
    """Budget consumption snapshot."""

    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    steps: int = 0
    elapsed_s: float = 0.0


class QueryResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    query: str
    answer: str
    sources: list[SourceItem]
    agent_type: str
    iterations: int
    tools_called: list[str]
    model: str
    cached: bool = False
    degraded: bool = False
    degradation_reasons: list[str] = Field(default_factory=list)
    usage: UsageInfoResponse = Field(default_factory=UsageInfoResponse)
    budget: BudgetInfoResponse = Field(default_factory=BudgetInfoResponse)
    metadata: dict[str, Any] = Field(default_factory=dict)
    api_version: str = __version__


class StreamChunk(BaseModel):
    """Individual chunk during streaming."""

    request_id: str
    delta: str
    done: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, bool]


class ReadinessResponse(BaseModel):
    """Deep readiness: state deps + tool registry, for K8s /readyz."""

    status: str                          # ready | degraded | not_ready
    version: str
    redis: bool
    tools: dict[str, bool]
    breaker_states: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standardized error — mirrors core.exceptions error codes."""

    error: str                           # stable error_code
    detail: str | None = None
    severity: str = "error"
    retryable: bool = False
    request_id: str = Field(default_factory=lambda: uuid4().hex)


class EvaluationRequest(BaseModel):
    query: str
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    ground_truth: str | None = None


class EvaluationResponse(BaseModel):
    scores: dict[str, float]
    feedback: dict[str, str]
    overall_score: float
    passed: bool
