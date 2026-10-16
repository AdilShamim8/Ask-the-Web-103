from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from agents import AgentType, build_agent
from api.cache import ResponseCache
from api.schemas import (
    AgentTypeRequest,
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
)
from configs.settings import get_settings
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from evaluation.evaluator import AnswerEvaluator
from workflows import build_routed_pipeline

logger = structlog.get_logger(__name__)
router = APIRouter()

# ── Dependency providers ──────────────────────────────────────────────────────

_cache: ResponseCache | None = None


def get_cache() -> ResponseCache:
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache


def get_evaluator() -> AnswerEvaluator:
    return AnswerEvaluator(llm_client=LLMClient())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _state_to_response(
    state: AgentState,
    agent_type: str,
    model: str,
    cached: bool = False,
) -> QueryResponse:
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
        metadata=state.metadata,
    )


async def _run_agent(req: QueryRequest) -> tuple[AgentState, str]:
    """Dispatch to the right agent/pipeline and return (state, agent_type_str)."""
    settings = get_settings()
    model = req.model or settings.default_model

    if req.agent_type == AgentTypeRequest.AUTO:
        state = await build_routed_pipeline(query=req.query, model=model)
        agent_type_str = "auto"
    else:
        agent_map = {
            AgentTypeRequest.REACT: AgentType.REACT,
            AgentTypeRequest.REFLEXION: AgentType.REFLEXION,
            AgentTypeRequest.ORCHESTRATOR: AgentType.ORCHESTRATOR,
        }
        agent = build_agent(
            agent_type=agent_map[req.agent_type],
            model=model,
            max_iterations=req.max_iterations,
        )
        state = await agent.run(req.query)
        agent_type_str = req.agent_type.value

    return state, agent_type_str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Service health check — verifies LLM provider availability."""
    settings = get_settings()

    providers: dict[str, bool] = {}

    # Check OpenAI
    try:
        llm = LLMClient()
        await llm.complete(
            messages=[Message(role=Role.USER, content="ping")],
            model="gpt-4o-mini",
            max_tokens=5,
        )
        providers["openai"] = True
    except Exception:
        providers["openai"] = False

    return HealthResponse(
        status="ok" if any(providers.values()) else "degraded",
        version="1.0.0",
        providers=providers,
    )


@router.post("/ask", response_model=QueryResponse, tags=["Agent"])
async def ask(
    req: QueryRequest,
    request: Request,
    cache: ResponseCache = Depends(get_cache),
) -> QueryResponse:
    """
    Main endpoint: send a query to the Ask-the-Web agent.
    Returns a structured answer with sources, citations, and metadata.
    """
    settings = get_settings()
    model = req.model or settings.default_model
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "api.ask",
        request_id=request_id,
        query=req.query[:80],
        agent_type=req.agent_type,
    )

    # ── Cache check ───────────────────────────────────────────────────────
    if not req.stream:
        cached = await cache.get(req.query, req.agent_type.value, model)
        if cached:
            logger.info("api.ask.cache_hit", request_id=request_id)
            return QueryResponse(**cached, cached=True)

    # ── Run agent ─────────────────────────────────────────────────────────
    state, agent_type_str = await _run_agent(req)

    response = _state_to_response(state, agent_type_str, model, cached=False)

    # ── Cache store ───────────────────────────────────────────────────────
    await cache.set(
        req.query,
        req.agent_type.value,
        model,
        response.model_dump(),
    )

    return response


@router.post("/ask/stream", tags=["Agent"])
async def ask_stream(req: QueryRequest, request: Request) -> StreamingResponse:
    """
    Streaming endpoint: runs the agent, then streams the final answer
    token by token using Server-Sent Events (SSE).
    """
    settings = get_settings()
    model = req.model or settings.default_model
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info("api.ask.stream", request_id=request_id, query=req.query[:80])

    async def event_generator() -> AsyncIterator[str]:
        try:
            # Run the agent to get tool results and context
            state, agent_type_str = await _run_agent(req)

            # Build messages for final streaming synthesis
            llm = LLMClient()

            # Send metadata first
            meta = {
                "type": "metadata",
                "request_id": request_id,
                "sources": state.sources,
                "iterations": state.iterations,
                "tools_called": [tc.name for tc in state.tool_calls_made],
            }
            yield f"data: {json.dumps(meta)}\n\n"

            # Stream the final answer
            from core.message_types import Message, Role
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
                messages=synthesis_messages,
                model=model,
            ):
                chunk = {"type": "token", "delta": token, "done": False}
                yield f"data: {json.dumps(chunk)}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'done', 'done': True})}\n\n"

        except Exception as exc:
            logger.error("stream.error", error=str(exc))
            error_chunk = {"type": "error", "error": str(exc)}
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/evaluate", response_model=EvaluationResponse, tags=["Evaluation"])
async def evaluate_answer(
    req: EvaluationRequest,
    evaluator: AnswerEvaluator = Depends(get_evaluator),
) -> EvaluationResponse:
    """
    Evaluate an answer for quality, accuracy, and completeness.
    Useful for CI pipelines and answer quality monitoring.
    """
    result = await evaluator.evaluate(
        query=req.query,
        answer=req.answer,
        sources=[s.model_dump() for s in req.sources],
        ground_truth=req.ground_truth,
    )
    return EvaluationResponse(**result)


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