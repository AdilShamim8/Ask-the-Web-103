from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class AgentTypeRequest(str, Enum):
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
        default=None,
        ge=1,
        le=20,
        description="Max reasoning iterations",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the final answer token-by-token",
    )

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        return v.strip()


class SourceItem(BaseModel):
    title: str
    url: str


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
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    """Individual chunk during streaming."""
    request_id: str
    delta: str
    done: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, bool]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
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