"""
Protocol routes — mount A2A server + MCP server on the API app.

ADR-004: this service both CONSUMES remote capabilities (MCP client,
A2A client) and EXPOSES its own (MCP server, A2A server). The exposed
surfaces go through the same guarded executor — external callers get
budgets, SSRF protection, and timeouts like everyone else.
"""

from __future__ import annotations

from fastapi import APIRouter

from agents.a2a import AgentCapability, AgentCard
from agents.a2a_server import create_a2a_server
from core import __version__
from tools.mcp_server import create_mcp_server


def _agent_card() -> AgentCard:
    """This service's A2A identity."""
    return AgentCard(
        agent_id="ask-the-web-agent",
        name="Ask-the-Web Agent",
        description=(
            "Cite-grounded web research agent: searches, scrapes, "
            "calculates, and synthesizes answers."
        ),
        version=__version__,
        url="",  # filled at mount time from request base URL by callers
        capabilities=[
            AgentCapability(
                name="web_research",
                description="Answer a research question with cited sources",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "sources": {"type": "array"},
                    },
                },
            ),
            AgentCapability(
                name="web_search",
                description="Raw web search returning ranked results",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                output_schema={"type": "object"},
            ),
        ],
        auth_required=False,  # edge handles auth in production deployments
    )


async def _handle_a2a_task(capability: str, input_data: dict) -> dict:
    """A2A task handler → routes to the right internal machinery."""
    if capability == "web_research":
        from agents import AgentType, build_agent
        from core.budgets import BudgetConfig, BudgetManager
        from core.usage_tracker import UsageTracker

        budget = BudgetManager(BudgetConfig.from_settings())
        usage = UsageTracker()
        agent = build_agent(
            AgentType.REACT, budget=budget, usage=usage,
        )
        state = await agent.run(input_data.get("query", ""))
        return {
            "answer": state.final_answer or "",
            "sources": state.sources,
            "usage": usage.to_dict(),
        }

    raise ValueError(
        f"Unknown capability: {capability}. "
        "Raw tool access is served via the MCP /mcp surface."
    )


def build_protocol_routers(request) -> tuple[APIRouter, APIRouter]:
    """
    Returns (a2a_router, mcp_router) bound to app singletons.

    Routers close over app.state singletons (registry, executor) which
    main.py builds at startup.
    """
    a2a_router = create_a2a_server(
        agent_card=_agent_card(),
        handler=_handle_a2a_task,
    )

    mcp_router = create_mcp_server(
        registry=request.app.state.tool_registry,
        executor=request.app.state.tool_executor,
    )
    return a2a_router, mcp_router
