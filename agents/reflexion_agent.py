"""
Reflexion Agent — ReACT + self-reflection loop.

Architecture:
    1. Run a ReACT agent for an initial answer
    2. A separate LLM evaluation critiques the answer (fast tier)
    3. On REVISE: re-run with the critique as context
    4. Repeat up to ``max_reflections`` (hard-capped)

Implements: Shinn et al., 2023 — "Reflexion: Language Agents with Verbal
Reinforcement Learning".

Production notes:
* The inner ReACT agent SHARES this agent's budget and usage tracker —
  otherwise every reflection round would restart the cost ceiling
  (ADR-005: fan-out multiplies cost, not the ceiling).
* ``max_reflections`` is clamped to 3. Reflection is the #2 cost-amplifier
  after tree search (FM-07): each round is a FULL re-run of research.
* Budget exhaustion mid-reflection returns the LAST good answer instead
  of failing the request — degrade, don't die.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agents.base_agent import BaseAgent
from agents.react_agent import ReACTAgent
from core.budgets import BudgetManager
from core.exceptions import BudgetExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from core.usage_tracker import UsageTracker
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)

_REFLECTION_PROMPT = """\
You are a critical evaluator. Review the following answer to the question below.

QUESTION: {query}

ANSWER:
{answer}

Evaluate on these dimensions:
1. ACCURACY   — Are claims supported by cited sources?
2. COMPLETENESS — Does it fully address the question?
3. CLARITY    — Is it well-structured and easy to read?
4. CITATIONS  — Are sources correctly referenced?

If the answer is satisfactory, respond with:
VERDICT: ACCEPT
REASON: <brief reason>

If the answer needs improvement, respond with:
VERDICT: REVISE
CRITIQUE: <specific critique>
SUGGESTION: <what to do differently>
"""

_REVISION_PROMPT = """\
Your previous answer was critiqued. Please revise it based on the feedback below.

ORIGINAL QUESTION: {query}

CRITIQUE:
{critique}

SUGGESTION:
{suggestion}

Please provide an improved, comprehensive answer. Re-search if needed.
"""


class ReflexionAgent(BaseAgent):
    """Reflexion: ReACT + verbal self-critique revision loop."""

    agent_name = "reflexion"

    MAX_REFLECTIONS = 3  # hard cap — each round is a full re-run (FM-07)

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        max_reflections: int = 2,
        *,
        budget: BudgetManager | None = None,
        usage: UsageTracker | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            llm_client, registry, executor, model, max_iterations,
            budget=budget, usage=usage, **kwargs,
        )
        self._max_reflections = max(1, min(max_reflections, self.MAX_REFLECTIONS))
        # Shared budget/usage: reflection rounds draw from the SAME pot.
        self._react = ReACTAgent(
            llm_client=llm_client,
            registry=registry,
            executor=executor,
            model=model,
            max_iterations=max_iterations,
            budget=self._budget,
            usage=self._usage,
        )

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        log = logger.bind(agent="Reflexion", query=query[:60])
        log.info("reflexion_agent.start")

        try:
            # ── Initial ReACT pass ────────────────────────────────────
            state = await self._react.run(query)
            log.info("reflexion.initial_answer_obtained")

            for reflection_round in range(self._max_reflections):
                self._budget.consume_step()

                verdict, critique, suggestion = await self._reflect(
                    query=query, answer=state.final_answer or "",
                )
                log.info(
                    "reflexion.verdict",
                    round=reflection_round + 1, verdict=verdict,
                )

                if verdict == "ACCEPT":
                    break

                log.info("reflexion.revising", critique=critique[:100])
                revised_query = _REVISION_PROMPT.format(
                    query=query, critique=critique, suggestion=suggestion,
                )
                state = await self._react.run(revised_query)

        except BudgetExceededError as exc:
            log.warning("reflexion.budget_exceeded", dimension=exc.dimension)
            # state holds the LAST completed round's answer — keep it.
            self._mark_budget_exceeded(state, exc)
            self._finish(state, start, outcome="budget_exceeded")
            return state

        self._finish(state, start)
        return state

    async def _reflect(
        self, query: str, answer: str
    ) -> tuple[str, str, str]:
        """Evaluate the answer. Returns (verdict, critique, suggestion)."""
        prompt = _REFLECTION_PROMPT.format(
            query=query, answer=answer[:8_000],
        )
        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM,
                        content="You are a rigorous answer evaluator."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.0,
            max_tokens=512,
            fast=True,  # critique is a checklist, not prose
            budget=self._budget,
            usage_tracker=self._usage,
        )

        return self._parse_reflection(response.content or "")

    def _parse_reflection(self, text: str) -> tuple[str, str, str]:
        """Parse the structured reflection output."""
        verdict = "ACCEPT"
        critique = ""
        suggestion = ""

        lines = text.strip().splitlines()
        for i, line in enumerate(lines):
            upper = line.upper()
            if "VERDICT:" in upper:
                verdict = "ACCEPT" if "ACCEPT" in upper else "REVISE"
            elif "CRITIQUE:" in upper:
                critique = line.split(":", 1)[-1].strip()
                for j in range(i + 1, len(lines)):
                    if any(k in lines[j].upper()
                           for k in ("SUGGESTION:", "VERDICT:")):
                        break
                    critique += " " + lines[j].strip()
            elif "SUGGESTION:" in upper:
                suggestion = line.split(":", 1)[-1].strip()
                for j in range(i + 1, len(lines)):
                    if "VERDICT:" in lines[j].upper():
                        break
                    suggestion += " " + lines[j].strip()

        return verdict.strip(), critique.strip(), suggestion.strip()
