from __future__ import annotations

import json
import time
from typing import Any

import structlog

from core.exceptions import MaxIterationsExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role, ToolResult
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry
from agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class ReACTAgent(BaseAgent):
    """
    ReACT (Reason + Act) Agent.

    Loop:
        1. THINK  — LLM reasons about what to do next
        2. ACT    — LLM calls one or more tools
        3. OBSERVE— Tool results fed back to LLM
        4. REPEAT — Until LLM produces a final text answer (no tool calls)

    The LLM signals it is done by returning a plain text message
    with no tool_calls attached.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        parallel_tools: bool = True,
    ) -> None:
        super().__init__(llm_client, registry, executor, model, max_iterations)
        self._parallel_tools = parallel_tools

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        state = self._build_initial_state(query)

        log = logger.bind(agent="ReACT", query=query[:60])
        log.info("react_agent.start")

        while True:
            self._check_iterations(state)
            self._trim_context(state)

            # ── THINK / ACT ──────────────────────────────────────────────
            state.iterations += 1
            log.debug("react.iteration", n=state.iterations)

            response: Message = await self._llm.complete(
                messages=state.messages,
                tools=self._get_tool_schemas(),
                model=self._model,
                temperature=0.0,
            )
            state.messages.append(response)

            # ── DONE? ────────────────────────────────────────────────────
            if not response.tool_calls:
                # LLM produced a final answer
                state.final_answer = response.content or ""
                break

            # ── OBSERVE ──────────────────────────────────────────────────
            state.tool_calls_made.extend(response.tool_calls)
            log.info(
                "react.tool_calls",
                tools=[tc.name for tc in response.tool_calls],
                n=state.iterations,
            )

            if self._parallel_tools and len(response.tool_calls) > 1:
                results = await self._executor.execute_parallel(response.tool_calls)
            else:
                results = await self._executor.execute_sequential(response.tool_calls)

            state.tool_results_received.extend(results)

            # Feed each result back as a separate tool message
            # (OpenAI requires one tool message per tool_call_id)
            for result in results:
                state.messages.append(
                    Message(
                        role=Role.TOOL,
                        tool_results=[result],
                    )
                )

        self._extract_sources(state)
        self._log_state_summary(state, time.perf_counter() - start)
        return state