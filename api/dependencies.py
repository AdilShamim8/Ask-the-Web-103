"""
API dependencies — request-scoped wiring (composition root for the HTTP layer).

Why this exists: the old routes built LLMClient / ResponseCache /
AnswerEvaluator ad hoc — including at module import for globals. That
meant uncontrolled client construction and zero test seams. Now:

* App-lifetime singletons live on ``app.state`` (built in lifespan).
* Request-scoped objects (budget, usage) are created per request via
  FastAPI Depends — one pair per request, shared by everything below.
* Tests override any dependency with ``app.dependency_overrides``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Request

from agents import AgentType, build_agent
from api.cache import ResponseCache
from core.budgets import BudgetConfig, BudgetManager
from core.llm_client import LLMClient
from core.usage_tracker import UsageTracker
from evaluation.evaluator import AnswerEvaluator


def get_cache(request: Request) -> ResponseCache:
    """App-lifetime response cache (from lifespan)."""
    return request.app.state.cache


def get_llm_client(request: Request) -> LLMClient:
    """App-lifetime shared LLM client (one provider pool per process)."""
    return request.app.state.llm_client


def get_evaluator(request: Request) -> AnswerEvaluator:
    return AnswerEvaluator(llm_client=request.app.state.llm_client)


def get_budget() -> BudgetManager:
    """Request-scoped budget — the anti-runaway guard (ADR-005)."""
    return BudgetManager(BudgetConfig.from_settings())


def get_usage() -> UsageTracker:
    """Request-scoped usage/cost accounting."""
    return UsageTracker()


def get_agent_factory(request: Request):
    """
    Returns a factory closure binding app singletons + request budget.
    Routes call: agent = factory(AgentType.REACT, model=...)
    """
    budget = get_budget()
    usage = get_usage()

    def _factory(agent_type: AgentType, **kwargs):
        return build_agent(
            agent_type,
            registry=request.app.state.tool_registry,
            budget=budget,
            usage=usage,
            **kwargs,
        )

    return _factory


# Annotated aliases for concise route signatures
CacheDep = Annotated[ResponseCache, None]  # replaced by Depends in routes
