from __future__ import annotations

"""
ReWOO (Reasoning WithOut Observation) Agent
Paper: Xu et al., 2023 — "ReWOO: Decoupling Reasoning from Observations
        for Efficient Augmented Language Models"

Key insight: Unlike ReACT which interleaves reasoning and tool calls,
ReWOO separates the entire plan UP FRONT, executes all tools in parallel,
then synthesizes. This reduces LLM calls from O(2N) to O(2) for N tool uses.

Flow:
    PLANNER  → produces a full plan: list of (thought, tool, args) steps
    EXECUTOR → runs all tool steps (in parallel where possible)
    SOLVER   → given plan + all observations, produces the final answer
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role, ToolCall, ToolResult
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)

_PLANNER_PROMPT = """\
You are a planning agent. Create a step-by-step plan to answer the question below.

For each step, specify:
- A thought explaining WHY this step is needed
- A tool to use (one of: {tool_names})
- The arguments for that tool

Format each step EXACTLY as:
Step N:
Thought: <why this step is needed>
Tool: <tool_name>
Args: <JSON object of arguments>

Example:
Step 1:
Thought: I need to search for current information about AI.
Tool: web_search
Args: {{"query": "latest AI developments 2024", "num_results": 5}}

Step 2:
Thought: I need to scrape the most relevant result for details.
Tool: scrape_webpage
Args: {{"url": "#E1.results[0].url"}}

Use #EN to reference the output of step N (evidence variable).
Create 2-5 steps. No more.

QUESTION: {query}
"""

_SOLVER_PROMPT = """\
Given the following plan and observations, provide a comprehensive answer.

ORIGINAL QUESTION: {query}

PLAN AND OBSERVATIONS:
{plan_with_observations}

Write a complete, well-cited answer using the observations above.
Include a Sources section at the end.
"""


@dataclass
class PlanStep:
    index: int
    thought: str
    tool_name: str
    raw_args: str          # May contain #E references
    resolved_args: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    tool_call_id: str = ""


class ReWOOAgent(BaseAgent):
    """
    ReWOO Agent: Plan-all-first, execute-in-parallel, solve-once.
    More token-efficient than ReACT for multi-step research tasks.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
    ) -> None:
        super().__init__(llm_client, registry, executor, model, max_iterations)

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        state = self._build_initial_state(query)
        log = logger.bind(agent="ReWOO", query=query[:60])
        log.info("rewoo.start")

        # ── Phase 1: PLAN ─────────────────────────────────────────────────
        plan_steps = await self._plan(query)
        log.info("rewoo.planned", num_steps=len(plan_steps))
        state.iterations += 1

        if not plan_steps:
            # Fallback: direct answer
            response = await self._llm.complete(
                messages=state.messages,
                model=self._model,
                temperature=0.0,
            )
            state.final_answer = response.content or ""
            state.iterations += 1
            self._log_state_summary(state, time.perf_counter() - start)
            return state

        # ── Phase 2: EXECUTE ──────────────────────────────────────────────
        plan_steps = await self._execute_plan(plan_steps)
        state.iterations += 1

        # Record tool calls in state
        for step in plan_steps:
            tc = ToolCall(
                id=step.tool_call_id,
                name=step.tool_name,
                arguments=step.resolved_args,
            )
            state.tool_calls_made.append(tc)
            tr = ToolResult(
                tool_call_id=step.tool_call_id,
                tool_name=step.tool_name,
                content=step.observation,
            )
            state.tool_results_received.append(tr)

        # ── Phase 3: SOLVE ────────────────────────────────────────────────
        final_answer = await self._solve(query, plan_steps)
        state.final_answer = final_answer
        state.iterations += 1

        self._extract_sources(state)
        self._log_state_summary(state, time.perf_counter() - start)
        return state

    async def _plan(self, query: str) -> list[PlanStep]:
        """Ask the planner LLM to produce a full step-by-step plan."""
        tool_names = ", ".join(
            t.name for t in self._registry.all_tools()
        )
        prompt = _PLANNER_PROMPT.format(query=query, tool_names=tool_names)

        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM, content="You are a meticulous planning agent."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.0,
            max_tokens=1024,
        )

        return self._parse_plan(response.content or "")

    def _parse_plan(self, text: str) -> list[PlanStep]:
        """Parse the planner output into structured PlanStep objects."""
        steps: list[PlanStep] = []
        # Split on "Step N:"
        raw_steps = re.split(r"Step\s+\d+:", text, flags=re.IGNORECASE)

        for i, block in enumerate(raw_steps[1:], 1):  # skip preamble
            thought_match = re.search(
                r"Thought:\s*(.+?)(?=Tool:|$)", block, re.DOTALL | re.IGNORECASE
            )
            tool_match = re.search(
                r"Tool:\s*(\w+)", block, re.IGNORECASE
            )
            args_match = re.search(
                r"Args:\s*(\{.+?\})", block, re.DOTALL | re.IGNORECASE
            )

            if not (thought_match and tool_match):
                continue

            tool_name = tool_match.group(1).strip()
            if tool_name not in self._registry:
                logger.warning("rewoo.unknown_tool", tool=tool_name)
                continue

            thought = thought_match.group(1).strip()
            raw_args = args_match.group(1).strip() if args_match else "{}"

            steps.append(PlanStep(
                index=i,
                thought=thought,
                tool_name=tool_name,
                raw_args=raw_args,
            ))

        return steps

    def _resolve_args(
        self, raw_args: str, evidence: dict[int, str]
    ) -> dict[str, Any]:
        """
        Replace #EN references with actual evidence from prior steps.
        E.g., "#E1" → observation of step 1.
        """
        resolved = raw_args
        for idx, obs in sorted(evidence.items(), reverse=True):
            resolved = resolved.replace(f"#E{idx}", obs[:500])

        try:
            return json.loads(resolved)
        except json.JSONDecodeError:
            # Best-effort: extract key-value pairs
            logger.warning("rewoo.args_parse_failed", raw=raw_args[:100])
            return {}

    async def _execute_plan(self, steps: list[PlanStep]) -> list[PlanStep]:
        """
        Execute plan steps in dependency order.
        Steps with no #E references can run in parallel.
        Steps with #E references run after their dependencies.
        """
        import asyncio
        evidence: dict[int, str] = {}

        # Group steps by dependency level
        independent = [s for s in steps if f"#E" not in s.raw_args]
        dependent   = [s for s in steps if f"#E" in s.raw_args]

        # Execute independent steps in parallel
        if independent:
            for step in independent:
                step.resolved_args = self._resolve_args(step.raw_args, {})

            tool_calls = [
                ToolCall(
                    name=s.tool_name,
                    arguments=s.resolved_args,
                )
                for s in independent
            ]
            results = await self._executor.execute_parallel(tool_calls)

            for step, tc, tr in zip(independent, tool_calls, results):
                step.tool_call_id = tc.id
                step.observation = tr.content
                evidence[step.index] = tr.content

        # Execute dependent steps sequentially (need prior evidence)
        for step in dependent:
            step.resolved_args = self._resolve_args(step.raw_args, evidence)
            tc = ToolCall(name=step.tool_name, arguments=step.resolved_args)
            tr = await self._executor.execute_one(tc)
            step.tool_call_id = tc.id
            step.observation = tr.content
            evidence[step.index] = tr.content

        return steps

    async def _solve(self, query: str, steps: list[PlanStep]) -> str:
        """Produce the final answer using all plan steps and observations."""
        plan_obs = ""
        for step in steps:
            plan_obs += (
                f"Step {step.index}:\n"
                f"  Thought: {step.thought}\n"
                f"  Tool: {step.tool_name}\n"
                f"  Observation: {step.observation[:1000]}\n\n"
            )

        prompt = _SOLVER_PROMPT.format(
            query=query,
            plan_with_observations=plan_obs,
        )

        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM, content="You are an expert research synthesizer."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.1,
            max_tokens=self._settings.max_tokens_per_response,
        )
        return response.content or ""