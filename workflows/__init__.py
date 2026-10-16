from __future__ import annotations

from typing import Any

import structlog

from agents import AgentType, build_agent
from configs.settings import get_settings
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from workflows.prompt_chaining import build_search_chain
from workflows.routing import QueryClassifier, QueryRouter, Route

logger = structlog.get_logger(__name__)


async def build_routed_pipeline(
    query: str,
    model: str | None = None,
) -> AgentState:
    """
    Full pipeline:
        1. Quick rule-based classification (free, no LLM call)
        2. LLM-based routing if unclear
        3. Dispatch to the right agent
    """
    settings = get_settings()
    llm = LLMClient()
    _model = model or settings.default_model

    # ── Quick classify ────────────────────────────────────────────────────
    quick_route = QueryClassifier.quick_classify(query)
    if quick_route == "conversational":
        response = await llm.complete(
            messages=[
                Message(role=Role.SYSTEM, content="You are a helpful assistant."),
                Message(role=Role.USER, content=query),
            ],
            model=_model,
        )
        state = AgentState(query=query)
        state.final_answer = response.content or ""
        return state

    # ── LLM routing ───────────────────────────────────────────────────────
    async def _react_handler(q: str, _: Any) -> AgentState:
        return await build_agent(AgentType.REACT, model=_model).run(q)

    async def _reflexion_handler(q: str, _: Any) -> AgentState:
        return await build_agent(AgentType.REFLEXION, model=_model).run(q)

    async def _orchestrator_handler(q: str, _: Any) -> AgentState:
        return await build_agent(AgentType.ORCHESTRATOR, model=_model).run(q)

    async def _calc_handler(q: str, _: Any) -> AgentState:
        # Calculator queries: minimal search + direct calc agent
        agent = build_agent(AgentType.REACT, model=_model, max_iterations=3)
        return await agent.run(q)

    router = QueryRouter(llm_client=llm, model=_model)
    router.add_route(Route(
        name="simple_qa",
        description="Short factual questions answerable with 1-2 searches",
        handler=_react_handler,
    ))
    router.add_route(Route(
        name="research",
        description="Complex research requiring deep analysis and verification",
        handler=_reflexion_handler,
    ))
    router.add_route(Route(
        name="multi_faceted",
        description="Multi-part questions covering several distinct topics",
        handler=_orchestrator_handler,
    ))
    router.add_route(Route(
        name="calculation",
        description="Math or unit conversion with minimal web context needed",
        handler=_calc_handler,
    ))

    route_name, result = await router.route(query)
    logger.info("pipeline.route_selected", route=route_name)

    if isinstance(result, AgentState):
        return result

    # Should not happen, but safe fallback
    fallback_state = AgentState(query=query)
    fallback_state.final_answer = str(result)
    return fallback_state