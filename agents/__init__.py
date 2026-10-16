"""
Agents package — reasoning strategies + factory.

Factory contract:
* ``build_agent`` wires shared singletons: LLMClient, ToolRegistry,
  ToolExecutor. Creating a NEW LLMClient per agent (old behavior) built a
  fresh provider client pool per request — socket churn at scale (FM-18).
* Optional ``budget`` / ``usage`` injection — the API layer creates one
  pair per request and passes them down so every strategy shares them.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any

from agents.base_agent import BaseAgent
from agents.orchestrator import OrchestratorAgent
from agents.planner import TaskPlanner
from agents.react_agent import ReACTAgent
from agents.reflexion_agent import ReflexionAgent
from agents.rewoo_agent import ReWOOAgent
from agents.tree_search_agent import TreeSearchAgent
from core.budgets import BudgetManager
from core.llm_client import LLMClient
from core.usage_tracker import UsageTracker
from tools import build_default_registry
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry


class AgentType(StrEnum):
    REACT = "react"
    REFLEXION = "reflexion"
    ORCHESTRATOR = "orchestrator"
    REWOO = "rewoo"
    TREE_SEARCH = "tree_search"


@lru_cache(maxsize=1)
def _shared_llm_client() -> LLMClient:
    """One provider client pool per process (FM-18)."""
    return LLMClient()


@lru_cache(maxsize=1)
def _shared_registry() -> ToolRegistry:
    """Boot-time tool registry (MCP discovery merges before freeze)."""
    return build_default_registry()


@lru_cache(maxsize=1)
def _shared_executor() -> ToolExecutor:
    return ToolExecutor(_shared_registry())


def build_agent(
    agent_type: AgentType = AgentType.REACT,
    model: str | None = None,
    max_iterations: int | None = None,
    registry: ToolRegistry | None = None,
    *,
    budget: BudgetManager | None = None,
    usage: UsageTracker | None = None,
    **kwargs: Any,
) -> BaseAgent:
    """
    Agent factory with shared infrastructure.

    ``budget``/``usage``: pass the request-scoped pair when running under
    the API; standalone runs (CLI, tests) get fresh ones automatically.
    """
    llm_client = _shared_llm_client()
    reg = registry or _shared_registry()
    executor = ToolExecutor(reg) if registry else _shared_executor()

    common: dict[str, Any] = dict(
        llm_client=llm_client,
        registry=reg,
        executor=executor,
        model=model,
        max_iterations=max_iterations,
        budget=budget,
        usage=usage,
    )

    agent_map: dict[AgentType, type[BaseAgent]] = {
        AgentType.REACT: ReACTAgent,
        AgentType.REFLEXION: ReflexionAgent,
        AgentType.ORCHESTRATOR: OrchestratorAgent,
        AgentType.REWOO: ReWOOAgent,
        AgentType.TREE_SEARCH: TreeSearchAgent,
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
