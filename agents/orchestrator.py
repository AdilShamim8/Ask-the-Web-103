from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

from agents.base_agent import BaseAgent, SYSTEM_PROMPT
from agents.react_agent import ReACTAgent
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
"""


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator-Worker Multi-Agent Pattern.

    Flow:
        1. ORCHESTRATOR: Decomposes the query into N sub-questions
        2. WORKERS: N parallel ReACT agents each answer one sub-question
        3. ORCHESTRATOR: Synthesizes all sub-answers into a final answer

    This enables parallelization and specialization for complex queries.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        max_workers: int = 4,
    ) -> None:
        super().__init__(llm_client, registry, executor, model, max_iterations)
        self._max_workers = max_workers

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        log = logger.bind(agent="Orchestrator", query=query[:60])
        log.info("orchestrator.start")

        master_state = self._build_initial_state(query)

        # ── Step 1: Decompose ────────────────────────────────────────────
        sub_questions = await self._decompose(query)
        log.info("orchestrator.decomposed", sub_questions=sub_questions)

        # ── Step 2: Dispatch workers in parallel ─────────────────────────
        worker_states = await self._run_workers(sub_questions)
        log.info("orchestrator.workers_done", num_workers=len(worker_states))

        # ── Step 3: Synthesize ───────────────────────────────────────────
        final_answer, all_sources = await self._synthesize(query, worker_states)

        master_state.final_answer = final_answer
        master_state.sources = all_sources
        master_state.metadata["sub_questions"] = sub_questions
        master_state.metadata["worker_iterations"] = [
            w.iterations for w in worker_states
        ]

        self._log_state_summary(master_state, time.perf_counter() - start)
        return master_state

    async def _decompose(self, query: str) -> list[str]:
        """Ask the LLM to split the query into sub-questions."""
        prompt = _DECOMPOSITION_PROMPT.format(query=query)
        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM, content="You are a task decomposition expert."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.0,
            max_tokens=512,
        )

        text = (response.content or "").strip()
        try:
            # Strip markdown code fences if present
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
            # Fallback: treat the original query as a single sub-question
            return [query]

    async def _run_workers(self, sub_questions: list[str]) -> list[AgentState]:
        """Spawn one ReACT worker per sub-question, all in parallel."""
        semaphore = asyncio.Semaphore(self._max_workers)

        async def _worker(question: str) -> AgentState:
            async with semaphore:
                agent = ReACTAgent(
                    llm_client=self._llm,
                    registry=self._registry,
                    executor=self._executor,
                    model=self._model,
                    max_iterations=self._max_iterations,
                )
                return await agent.run(question)

        tasks = [_worker(q) for q in sub_questions]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    async def _synthesize(
        self, query: str, worker_states: list[AgentState]
    ) -> tuple[str, list[dict[str, str]]]:
        """Merge all worker answers into a coherent final answer."""
        sub_answers_text = ""
        all_sources: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for i, ws in enumerate(worker_states, 1):
            sub_answers_text += (
                f"\n--- Sub-answer {i} ---\n"
                f"Question: {ws.query}\n"
                f"Answer: {ws.final_answer or 'No answer produced.'}\n"
            )
            for src in ws.sources:
                url = src.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append(src)

        prompt = _SYNTHESIS_PROMPT.format(
            query=query,
            sub_answers=sub_answers_text,
        )

        response = await self._llm.complete(
            messages=[
                Message(role=Role.SYSTEM, content="You are an expert synthesis writer."),
                Message(role=Role.USER, content=prompt),
            ],
            model=self._model,
            temperature=0.2,
            max_tokens=self._settings.max_tokens_per_response,
        )

        return response.content or "", all_sources