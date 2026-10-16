# agents/__init__.py  — COMPLETE version with all agents
from __future__ import annotations

from enum import Enum
from typing import Any

from agents.base_agent import BaseAgent
from agents.orchestrator import OrchestratorAgent
from agents.planner import TaskPlanner
from agents.react_agent import ReACTAgent
from agents.reflexion_agent import ReflexionAgent
from agents.rewoo_agent import ReWOOAgent
from agents.tree_search_agent import TreeSearchAgent
from core.llm_client import LLMClient
from tools import build_default_registry
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry


class AgentType(str, Enum):
    REACT       = "react"
    REFLEXION   = "reflexion"
    ORCHESTRATOR= "orchestrator"
    REWOO       = "rewoo"
    TREE_SEARCH = "tree_search"


def build_agent(
    agent_type: AgentType = AgentType.REACT,
    model: str | None = None,
    max_iterations: int | None = None,
    registry: ToolRegistry | None = None,
    **kwargs: Any,
) -> BaseAgent:
    """
    Agent factory. Creates a fully-wired agent with shared
    LLM client, tool registry, and executor.
    """
    llm_client = LLMClient()
    registry = registry or build_default_registry()
    executor = ToolExecutor(registry)

    common: dict[str, Any] = dict(
        llm_client=llm_client,
        registry=registry,
        executor=executor,
        model=model,
        max_iterations=max_iterations,
    )

    agent_map: dict[AgentType, type[BaseAgent]] = {
        AgentType.REACT:        ReACTAgent,
        AgentType.REFLEXION:    ReflexionAgent,
        AgentType.ORCHESTRATOR: OrchestratorAgent,
        AgentType.REWOO:        ReWOOAgent,
        AgentType.TREE_SEARCH:  TreeSearchAgent,
    }

    if agent_type not in agent_map:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return agent_map[agent_type](**common, **kwargs)


__all__ = [
    "AgentType",
    "BaseAgent",
    "ReACTAgent",
    "ReflexionAgent",
    "OrchestratorAgent",
    "ReWOOAgent",
    "TreeSearchAgent",
    "TaskPlanner",
    "build_agent",
]