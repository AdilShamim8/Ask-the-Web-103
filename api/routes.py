"""
API routes — the HTTP surface.

Key production fixes vs 1.0:
* ``/health`` no longer makes a PAID LLM CALL (the old check cost a
  real completion on every probe — monitoring was our biggest source of
  waste). Cheap liveness is process-level; deep checks live in /readyz.
* ``/ask`` runs through singleflight get_or_compute (ADR-003) — cache
  hits never recompute under load, misses compute exactly once.
* Budgets/usage are request-scoped via dependencies and returned in the
  response (cost transparency).
* Streaming uses the heartbeat-guarded SSE wrapper (api/streaming.py).
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agents import AgentType
from api import dependencies as deps
from api.cache import ResponseCache
from api.schemas import (
    AgentTypeRequest,
    EvaluationRequest,
    EvaluationResponse,
    QueryRequest,
    QueryResponse,
    ReadinessResponse,
    SourceItem,
    UsageInfoResponse,
    BudgetInfoResponse,
    HealthResponse,
)
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from evaluation.evaluator import AnswerEvaluator
from workflows import build_routed_pipeline

logger = structlog.get_logger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _state_to_response(
    state: AgentState,
    agent_type: str,
    model: str,
    cached: bool = False,
) -> QueryResponse:
    usage_meta = state.metadata.get("usage", {})
    budget_meta = state.metadata.get("budget", {})
    return QueryResponse(
        query=state.query,
        answer=state.final_answer or "",
        sources=[
            SourceItem(title=s.get("title", s["url"]), url=s["url"])
            for s in state.sources
        ],
        agent_type=agent_type,
        iterations=state.iterations,
        tools_called=[tc.name for tc in state.tool_calls_made],
        model=model,
        cached=cached,
        degraded=state.degraded,
        degradation_reasons=state.degradation_reasons,
        usage=UsageInfoResponse(
            llm_calls=usage_meta.get("llm_calls", 0),
            input_tokens=usage_meta.get("input_tokens", 0),
            output_tokens=usage_meta.get("output_tokens", 0),
            tool_calls=usage_meta.get("tool_calls", 0),
            web_searches=usage_meta.get("web_searches", 0),
            pages_fetched=usage_meta.get("pages_fetched", 0),
            estimated_cost_usd=usage_meta.get("estimated_cost_usd", 0.0),
        ),
        budget=BudgetInfoResponse(**budget_meta) if budget_meta else BudgetInfoResponse(),
        metadata={
            k: v for k, v in state.metadata.items()
            if k not in ("usage", "budget")
        },
    )


async def _run_agent(
    req: QueryRequest,
    request: Request,
    factory,
) -> tuple[AgentState, str]:
    """Dispatch to the right agent/pipeline. Returns (state, agent_str)."""
    from configs.settings import get_settings

    settings = get_settings()
    model = req.model or settings.default_model

    if req.agent_type == AgentTypeRequest.AUTO:
        state = await build_routed_pipeline(query=req.query, model=model)
        return state, "auto"

    agent_map = {
        AgentTypeRequest.REACT: AgentType.REACT,
        AgentTypeRequest.REFLEXION: AgentType.REFLEXION,
        AgentTypeRequest.ORCHESTRATOR: AgentType.ORCHESTRATOR,
    }
    agent = factory(
        agent_map[req.agent_type],
        model=model,
        max_iterations=req.max_iterations,
    )
    state = await agent.run(req.query)
    return state, req.agent_type.value


# ── System ────────────────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse, tags=["System"])
@router.get("/healthz", response_model=HealthResponse, tags=["System"],
            include_in_schema=False)
async def health_check(request: Request) -> HealthResponse:
    """
    Liveness: is the process serving HTTP? CHEAP by contract —
    no provider calls, no Redis round-trips. K8s liveness probes hit
    this; it must never fail because a dependency is slow (that's what
    readiness is for). Deep checks: /readyz.
    """
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        version=settings.api_version,
        providers={},  # intentionally empty — see /readyz
    )


@router.get("/readyz", response_model=ReadinessResponse, tags=["System"])
async def readiness_check(request: Request) -> ReadinessResponse:
    """
    Readiness: should this pod receive traffic? Checks state
    dependencies and the tool registry. A pod with a dead Redis still
    reports ready=true (cache fails open) but flags it.
    """
    app = request.app
    settings = app.state.settings

    redis_ok = True
    try:
        if app.state.cache is not None:
            redis_ok = await app.state.cache._get_client() is not None
    except Exception:
        redis_ok = False

    tools = {}
    try:
        tools = await app.state.tool_registry.health()
    except Exception:
        tools = {"registry": False}

    breakers = {
        s["name"]: s["state"]
        for s in app.state.llm_client.breaker_stats()
    }

    critical_tools_ok = tools.get("web_search", True)
    status = "ready" if critical_tools_ok else "degraded"

    return ReadinessResponse(
        status=status,
        version=settings.api_version,
        redis=redis_ok,
        tools=tools,
        breaker_states=breakers,
    )


# ── Agent ─────────────────────────────────────────────────────────────────────


@router.post("/ask", response_model=QueryResponse, tags=["Agent"])
async def ask(
    req: QueryRequest,
    request: Request,
    cache: ResponseCache = Depends(deps.get_cache),
    factory=Depends(deps.get_agent_factory),
) -> QueryResponse:
    """
    Main endpoint: query → cited answer. Singleflight-protected.
    """
    from configs.settings import get_settings

    settings = get_settings()
    model = req.model or settings.default_model
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "api.ask", request_id=request_id,
        query=req.query[:80], agent_type=req.agent_type,
    )

    async def _compute() -> dict[str, Any]:
        state, agent_str = await _run_agent(req, request, factory)
        return _state_to_response(
            state, agent_str, model, cached=False
        ).model_dump()

    if req.use_cache:
        value, computed = await cache.get_or_compute(
            req.query, req.agent_type.value, model, _compute
        )
        response = QueryResponse(**value)
        if not computed:
            response.cached = True
            logger.info("api.ask.cache_hit", request_id=request_id)
        return response

    return QueryResponse(**await _compute())


@router.post("/ask/stream", tags=["Agent"])
async def ask_stream(
    req: QueryRequest,
    request: Request,
    factory=Depends(deps.get_agent_factory),
) -> StreamingResponse:
    """
    Streaming endpoint (SSE): metadata first, then answer tokens with
    heartbeats, then done. Client disconnect stops the work.
    """
    from configs.settings import get_settings

    settings = get_settings()
    model = req.model or settings.default_model
    request_id = getattr(request.state, "request_id", "unknown")
    llm: LLMClient = request.app.state.llm_client

    logger.info("api.ask.stream", request_id=request_id, query=req.query[:80])

    async def event_producer() -> AsyncIterator[dict[str, Any]]:
        state, agent_str = await _run_agent(req, request, factory)

        yield {
            "event": "metadata",
            "data": {
                "request_id": request_id,
                "sources": state.sources,
                "iterations": state.iterations,
                "tools_called": [tc.name for tc in state.tool_calls_made],
                "degraded": state.degraded,
                "degradation_reasons": state.degradation_reasons,
            },
        }

        synthesis_messages = [
            Message(
                role=Role.SYSTEM,
                content=(
                    "Provide the final answer based on prior research. "
                    "Use markdown formatting and cite sources."
                ),
            ),
            Message(
                role=Role.USER,
                content=(
                    f"Question: {req.query}\n\n"
                    f"Research findings:\n{state.final_answer}"
                ),
            ),
        ]

        async for token in llm.stream_complete(
            messages=synthesis_messages, model=model,
        ):
            yield {"event": "token", "data": {"delta": token}}

        yield {"event": "done", "data": {"done": True}}

    from api.streaming import sse_stream

    async def _is_disconnected() -> bool:
        return await request.is_disconnected()

    return StreamingResponse(
        sse_stream(producer=event_producer(), is_disconnected=_is_disconnected),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Evaluation ────────────────────────────────────────────────────────────────


@router.post("/evaluate", response_model=EvaluationResponse, tags=["Evaluation"])
async def evaluate_answer(
    req: EvaluationRequest,
    evaluator: AnswerEvaluator = Depends(deps.get_evaluator),
) -> EvaluationResponse:
    """Evaluate an answer for quality — CI pipelines and monitoring."""
    result = await evaluator.evaluate(
        query=req.query,
        answer=req.answer,
        sources=[s.model_dump() for s in req.sources],
        ground_truth=req.ground_truth,
    )
    return EvaluationResponse(**result)


# ── Model catalog ─────────────────────────────────────────────────────────────


@router.get("/models", tags=["System"])
async def list_models() -> dict[str, list[str]]:
    """List available models per provider."""
    return {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ],
    }
