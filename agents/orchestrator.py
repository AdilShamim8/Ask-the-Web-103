"""
Orchestrator-Worker Agent (LLM-decided decomposition).

Flow:
    1. ORCHESTRATOR: decomposes the query into N sub-questions
    2. WORKERS: N parallel ReACT agents answer sub-questions
    3. ORCHESTRATOR: synthesizes sub-answers into one final answer

Production guarantees (FM-13):
* WORKER ISOLATION: one worker crashing (LLM error, budget, bad parse)
  yields a "no answer produced" placeholder for its section — its
  siblings complete and synthesis still happens. The old version used
  ``gather(return_exceptions=False)``: one worker failure failed the WHOLE
  request.
* SHARED BUDGET: all workers draw from the parent request budget; the
  fan-out multiplies cost but never the ceiling (ADR-005).
* PARTIAL DEGRADATION: if any worker failed, the answer is marked
  degraded and synthesis is told which sections are missing — the user
  gets an honest answer, not a confident gap.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

from agents.base_agent import BaseAgent
from agents.react_agent import ReACTAgent
from core.exceptions import BudgetExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)

_DECOMPOSITION_PROMPT = """\
You are a task decomposition expert.

Break the following complex question into 2-5 independent sub-questions
that, when answered together, will fully answer the original question.

QUESTION: {query}

Respond with a JSON array of sub-questions, e.g.:
["sub-question 1", "sub-question 2", "sub-question 3"]

Only output valid JSON. No explanation.
"""

_SYNTHESIS_PROMPT = """\
You are a synthesis expert. Combine the following sub-answers into one
comprehensive, well-structured answer to the original question.

ORIGINAL QUESTION:
{query}

SUB-ANSWERS:
{sub_answers}

Rules:
- Merge overlapping information
- Resolve any contradictions by noting them explicitly
- Use headers for different aspects of the answer
- Preserve all source citations from sub-answers
- Add a unified Sources section at the end
- Where a sub-answer is marked UNAVAILABLE, state plainly that this
  aspect could not be researched in this response — do not invent it.
"""


class OrchestratorAgent(BaseAgent):
    """Orchestrator-Worker multi-agent pattern."""

    agent_name = "orchestrator"

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        max_workers: int = 4,
        **kwargs: Any,
    ) -> None:
        super().__init__(llm_client, registry, executor, model,
                         max_iterations, **kwargs)
        self._max_workers = max(1, min(max_workers, 6))

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        log = logger.bind(agent="Orchestrator", query=query[:60])
        log.info("orchestrator.start")

        master_state = self._build_initial_state(query)

        try:
            # ── Step 1: Decompose ────────────────────────────────────
            self._budget.consume_step()
            sub_questions = await self._decompose(query)
            log.info("orchestrator.decomposed", sub_questions=sub_questions)

            # ── Step 2: Dispatch workers (isolated) ──────────────────
            worker_states = await self._run_workers(sub_questions)
            failed = sum(
                1 for ws in worker_states
                if isinstance(ws, BaseException) or ws.final_answer is None
            )
            if failed:
                log.warning(
                    "orchestrator.workers_partial_failure",
                    failed=failed, total=len(worker_states),
                )
                master_state.degraded = True
                master_state.degradation_reasons.append(
                    f"{failed}/{len(worker_states)} workers failed"
                )
            usable = [
                ws for ws in worker_states
                if not isinstance(ws, BaseException) and ws.final_answer is not None
            ]
            log.info("orchestrator.workers_done", num_ok=len(usable))

            # ── Step 3: Synthesize ───────────────────────────────────
            self._budget.consume_step()
            final_answer, all_sources = await self._synthesize(query, worker_states)

            master_state.final_answer = final_answer
            master_state.sources = all_sources
            master_state.metadata["sub_questions"] = sub_questions
            master_state.metadata["worker_iterations"] = [
                ws.iterations
                for ws in worker_states if not isinstance(ws, BaseException)
            ]

        except BudgetExceededError as exc:
            log.warning("orchestrator.budget_exceeded", dimension=exc.dimension)
            self._mark_budget_exceeded(master_state, exc)
            self._finish(master_state, start, outcome="budget_exceeded")
            return master_state

        self._finish(master_state, start)
        return master_state

    async def _decompose(self, query: str) -> list[str]:
        """Split the query into sub-questions (fallback: the query itself)."""
        prompt = _DECOMPOSITION_PROMPT.format(query=query)
        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM,
                        content="You are a task decomposition expert."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.0,
            max_tokens=512,
            fast=True,
            budget=self._budget,
            usage_tracker=self._usage,
        )

        text = (response.content or "").strip()
        try:
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            sub_questions = json.loads(text)
            if not isinstance(sub_questions, list):
                raise ValueError("Not a list")
            return [str(q) for q in sub_questions[: self._max_workers]]
        except (json.JSONDecodeError, ValueError):
            logger.warning("orchestrator.decompose_failed", raw=text[:200])
            return [query]  # fallback: single sub-question = the query

    async def _run_workers(self, sub_questions: list[str]) -> list[Any]:
        """
        One ReACT worker per sub-question, in parallel, all isolated.

        Returns a mixed list: AgentState for successes, Exception for
        failures — callers filter. Workers SHARE the parent budget.
        """
        semaphore = asyncio.Semaphore(self._max_workers)

        async def _worker(question: str) -> AgentState:
            async with semaphore:
                agent = ReACTAgent(
                    llm_client=self._llm,
                    registry=self._registry,
                    executor=self._executor,
                    model=self._model,
                    max_iterations=self._max_iterations,
                    budget=self._budget,      # shared ceiling
                    usage=self._usage,        # shared accounting
                )
                return await agent.run(question)

        tasks = [_worker(q) for q in sub_questions]
        # return_exceptions=True: isolation is THE point of this pattern.
        return list(await asyncio.gather(*tasks, return_exceptions=True))

    async def _synthesize(
        self, query: str, worker_states: list[Any]
    ) -> tuple[str, list[dict[str, str]]]:
        """Merge all worker answers into one coherent final answer."""
        sub_answers_text = ""
        all_sources: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for i, ws in enumerate(worker_states, 1):
            if isinstance(ws, BaseException):
                sub_answers_text += (
                    f"\n--- Sub-answer {i} ---\n"
                    f"Status: UNAVAILABLE (worker error: {type(ws).__name__})\n"
                )
                continue

            answer = ws.final_answer or "UNAVAILABLE (worker produced no answer)"
            sub_answers_text += (
                f"\n--- Sub-answer {i} ---\n"
                f"Question: {ws.query}\n"
                f"Answer: {answer}\n"
            )
            for src in ws.sources:
                url = src.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append(src)

        prompt = _SYNTHESIS_PROMPT.format(
            query=query, sub_answers=sub_answers_text,
        )

        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM,
                        content="You are an expert synthesis writer."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.2,
            max_tokens=self._settings.max_tokens_per_response,
            budget=self._budget,
            usage_tracker=self._usage,
        )

        return response.content or "", all_sources
