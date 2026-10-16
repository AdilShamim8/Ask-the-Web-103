"""
ReACT Agent — Reason + Act loop.

Loop:
    1. THINK  — LLM reasons about what to do next
    2. ACT    — LLM calls one or more tools
    3. OBSERVE— Tool results fed back to LLM
    4. REPEAT — until a final text answer (no tool_calls) or budget/iteration
                guard terminates the loop

Production notes:
* Budget + usage are checked on EVERY iteration (deadline, steps, tokens)
  — see base_agent. A hostile or confused model cannot loop forever.
* AGENT_RUNS telemetry with outcome labels: ok | budget_exceeded |
  max_iterations — runaway behavior is measurable, not mysterious.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base_agent import BaseAgent
from core.exceptions import BudgetExceededError, MaxIterationsExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from core.observability import AGENT_RUNS
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)


class ReACTAgent(BaseAgent):
    """ReACT (Reason + Act) Agent."""

    agent_name = "react"

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        parallel_tools: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(llm_client, registry, executor, model,
                         max_iterations, **kwargs)
        self._parallel_tools = parallel_tools

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        state = self._build_initial_state(query)

        log = logger.bind(agent="ReACT", query=query[:60])
        log.info("react_agent.start")

        try:
            while True:
                # ── Guards BEFORE every iteration (FM-06) ────────────
                self._budget.check_deadline()
                self._check_iterations(state)
                self._budget.consume_step()
                self._trim_context(state)

                state.iterations += 1
                log.debug("react.iteration", n=state.iterations)

                # ── THINK / ACT ──────────────────────────────────────
                response: Message = await self._llm.complete(
                    messages=state.messages,
                    tools=self._get_tool_schemas(),
                    model=self._model,
                    temperature=0.0,
                    budget=self._budget,
                    usage_tracker=self._usage,
                )
                state.messages.append(response)

                # ── DONE? ────────────────────────────────────────────
                if not response.tool_calls:
                    state.final_answer = response.content or ""
                    break

                # ── OBSERVE ──────────────────────────────────────────
                state.tool_calls_made.extend(response.tool_calls)
                log.info(
                    "react.tool_calls",
                    tools=[tc.name for tc in response.tool_calls],
                    n=state.iterations,
                )

                if self._parallel_tools and len(response.tool_calls) > 1:
                    results = await self._executor.execute_parallel(
                        response.tool_calls,
                        budget=self._budget,
                        usage=self._usage,
                    )
                else:
                    results = await self._executor.execute_sequential(
                        response.tool_calls,
                        budget=self._budget,
                        usage=self._usage,
                    )

                state.tool_results_received.extend(results)

                for result in results:
                    state.messages.append(
                        Message(role=Role.TOOL, tool_results=[result])
                    )

        except BudgetExceededError as exc:
            # Controlled termination — degrade with partial evidence.
            log.warning("react.budget_exceeded", dimension=exc.dimension)
            self._mark_budget_exceeded(state, exc)
            self._finish(state, start, outcome="budget_exceeded")
            return state

        except MaxIterationsExceededError:
            AGENT_RUNS.labels(agent_type=self.agent_name,
                              outcome="max_iterations").inc()
            state.degraded = True
            state.degradation_reasons.append("max_iterations")
            state.final_answer = self._partial_answer(state)
            self._finish(state, start, outcome="max_iterations")
            return state

        self._extract_sources(state)
        self._finish(state, start)
        return state
