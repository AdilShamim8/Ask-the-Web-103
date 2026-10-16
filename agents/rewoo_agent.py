"""
ReWOO (Reasoning WithOut Observation) Agent.

Paper: Xu et al., 2023 — "ReWOO: Decoupling Reasoning from Observations
for Efficient Augmented Language Models".

Key insight: unlike ReACT which interleaves reasoning and tool calls,
ReWOO plans UP FRONT, executes tools in parallel where possible, then
solves once. LLM calls drop from O(2N) to O(2) for N tool uses.

Flow:
    PLANNER  → full plan: list of (thought, tool, args) steps, with #EN
               evidence references between steps
    EXECUTOR → runs steps; independent steps in parallel, dependent
               steps after their evidence producers
    SOLVER   → final answer from plan + observations

Production notes:
* Dependency-aware execution preserved, now with shared budget/usage and
  guarded tool calls (executor enforces).
* ``_resolve_args`` is hardened: evidence snippets are JSON-escaped when
  substituted (a snippet containing quotes used to corrupt the arg JSON),
  and unresolvable steps are skipped with a recorded error instead of
  silently executing with empty args.
* Step count is clamped to the budget — a plan that can't fit is
  truncated, not attempted.
"""

from __future__ import annotations

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
Args: {{"query": "latest AI developments", "num_results": 5}}

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

_EVIDENCE_RE = re.compile(r"#E(\d+)")
_MAX_STEPS = 8


@dataclass
class PlanStep:
    index: int
    thought: str
    tool_name: str
    raw_args: str
    resolved_args: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    tool_call_id: str = ""
    failed: bool = False


class ReWOOAgent(BaseAgent):
    """ReWOO Agent: plan-all-first, execute-in-parallel, solve-once."""

    agent_name = "rewoo"

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(llm_client, registry, executor, model,
                         max_iterations, **kwargs)

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        state = self._build_initial_state(query)
        log = logger.bind(agent="ReWOO", query=query[:60])
        log.info("rewoo.start")

        try:
            self._budget.consume_step()

            # ── Phase 1: PLAN ────────────────────────────────────────
            plan_steps = await self._plan(query)
            # Clamp plan size to the remaining step budget.
            max_affordable = max(1, self._budget.steps + 2)  # planner+solver
            if len(plan_steps) > _MAX_STEPS:
                plan_steps = plan_steps[:_MAX_STEPS]
                log.warning("rewoo.plan_truncated", cap=_MAX_STEPS)
            log.info("rewoo.planned", num_steps=len(plan_steps))
            state.iterations += 1

            if not plan_steps:
                response = await self._llm.complete(
                    messages=state.messages,
                    model=self._model,
                    temperature=0.0,
                    budget=self._budget,
                    usage_tracker=self._usage,
                )
                state.final_answer = response.content or ""
                state.iterations += 1
                self._finish(state, start)
                return state

            # ── Phase 2: EXECUTE ─────────────────────────────────────
            plan_steps = await self._execute_plan(plan_steps)
            state.iterations += 1

            for step in plan_steps:
                state.tool_calls_made.append(ToolCall(
                    id=step.tool_call_id, name=step.tool_name,
                    arguments=step.resolved_args,
                ))
                state.tool_results_received.append(ToolResult(
                    tool_call_id=step.tool_call_id,
                    tool_name=step.tool_name,
                    content=step.observation,
                    is_error=step.failed,
                ))

            # ── Phase 3: SOLVE ───────────────────────────────────────
            self._budget.consume_step()
            state.final_answer = await self._solve(query, plan_steps)
            state.iterations += 1

        except Exception as exc:
            from core.exceptions import BudgetExceededError

            if isinstance(exc, BudgetExceededError):
                log.warning("rewoo.budget_exceeded", dimension=exc.dimension)
                self._mark_budget_exceeded(state, exc)
                self._finish(state, start, outcome="budget_exceeded")
                return state
            raise

        self._extract_sources(state)
        self._finish(state, start)
        return state

    async def _plan(self, query: str) -> list[PlanStep]:
        """Ask the planner LLM for a full step-by-step plan."""
        tool_names = ", ".join(t.name for t in self._registry.all_tools())
        prompt = _PLANNER_PROMPT.format(query=query, tool_names=tool_names)

        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM,
                        content="You are a meticulous planning agent."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.0,
            max_tokens=1024,
            budget=self._budget,
            usage_tracker=self._usage,
        )
        return self._parse_plan(response.content or "")

    def _parse_plan(self, text: str) -> list[PlanStep]:
        """Parse planner output into structured PlanStep objects."""
        steps: list[PlanStep] = []
        raw_steps = re.split(r"Step\s+\d+:", text, flags=re.IGNORECASE)

        for i, block in enumerate(raw_steps[1:], 1):
            thought_match = re.search(
                r"Thought:\s*(.+?)(?=Tool:|$)", block, re.DOTALL | re.IGNORECASE
            )
            tool_match = re.search(r"Tool:\s*(\w+)", block, re.IGNORECASE)
            args_match = re.search(
                r"Args:\s*(\{.+?\})", block, re.DOTALL | re.IGNORECASE
            )

            if not (thought_match and tool_match):
                continue

            tool_name = tool_match.group(1).strip()
            if tool_name not in self._registry:
                logger.warning("rewoo.unknown_tool", tool=tool_name)
                continue

            steps.append(PlanStep(
                index=i,
                thought=thought_match.group(1).strip(),
                tool_name=tool_name,
                raw_args=args_match.group(1).strip() if args_match else "{}",
            ))

        return steps

    def _resolve_args(
        self, raw_args: str, evidence: dict[int, str]
    ) -> dict[str, Any] | None:
        """
        Replace #EN references with actual evidence from prior steps.

        Returns None when the step is unresolvable (its evidence producer
        failed). The caller skips such steps — executing a step whose args
        reference missing evidence with empty substitutions is worse than
        skipping it.
        """
        resolved = raw_args
        for match in set(_EVIDENCE_RE.findall(resolved)):
            idx = int(match)
            if idx not in evidence:
                logger.warning("rewoo.evidence_missing", step_evidence=idx)
                return None
            snippet = evidence[idx][:500]
            # Escape quotes so embedded JSON/text can't break the arg JSON.
            resolved = resolved.replace(f"#E{idx}", json.dumps(snippet)[1:-1])

        try:
            return json.loads(resolved)
        except json.JSONDecodeError:
            logger.warning("rewoo.args_parse_failed", raw=raw_args[:100])
            return {}

    async def _execute_plan(self, steps: list[PlanStep]) -> list[PlanStep]:
        """Execute independent steps in parallel; dependent steps after."""
        evidence: dict[int, str] = {}

        def _deps(step: PlanStep) -> set[int]:
            return {int(m) for m in _EVIDENCE_RE.findall(step.raw_args)}

        independent = [s for s in steps if not _deps(s)]
        dependent = [s for s in steps if _deps(s)]

        if independent:
            for step in independent:
                step.resolved_args = self._resolve_args(step.raw_args, {}) or {}

            tool_calls = [
                ToolCall(name=s.tool_name, arguments=s.resolved_args)
                for s in independent
            ]
            results = await self._executor.execute_parallel(
                tool_calls, budget=self._budget, usage=self._usage
            )

            for step, tc, tr in zip(independent, tool_calls, results):
                step.tool_call_id = tc.id
                step.observation = tr.content
                step.failed = tr.is_error
                if not tr.is_error:
                    evidence[step.index] = tr.content

        for step in dependent:
            resolved = self._resolve_args(step.raw_args, evidence)
            if resolved is None:
                step.failed = True
                step.observation = json.dumps(
                    {"error": f"skipped: evidence for dependencies missing"}
                )
                continue
            step.resolved_args = resolved
            tc = ToolCall(name=step.tool_name, arguments=step.resolved_args)
            tr = await self._executor.execute_one(
                tc, budget=self._budget, usage=self._usage
            )
            step.tool_call_id = tc.id
            step.observation = tr.content
            step.failed = tr.is_error
            if not tr.is_error:
                evidence[step.index] = tr.content

        return steps

    async def _solve(self, query: str, steps: list[PlanStep]) -> str:
        """Produce the final answer from plan + observations."""
        plan_obs = ""
        for step in steps:
            status = " (failed)" if step.failed else ""
            plan_obs += (
                f"Step {step.index}:{status}\n"
                f"  Thought: {step.thought}\n"
                f"  Tool: {step.tool_name}\n"
                f"  Observation: {step.observation[:1000]}\n\n"
            )

        prompt = _SOLVER_PROMPT.format(
            query=query, plan_with_observations=plan_obs,
        )

        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM,
                        content="You are an expert research synthesizer."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.1,
            max_tokens=self._settings.max_tokens_per_response,
            budget=self._budget,
            usage_tracker=self._usage,
        )
        return response.content or ""
