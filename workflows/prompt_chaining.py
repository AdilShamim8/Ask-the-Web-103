"""
Prompt Chaining Workflow — deterministic multi-step pipelines.

Pattern: each step formats a prompt from prior outputs, calls the LLM,
and stores its result under ``output_key``. Fixed topology, predictable
cost — the most debuggable workflow shape.

Production hardening:
* Every LLM call runs through the request budget (ADR-005) and the fast
  model tier by default — chains are usually internal plumbing, not
  user-facing prose.
* Step failures fail fast with the step name in the error (no silent
  propagation of KeyError garbage).
* ``stop_if`` predicates allow early exit (e.g., skip synthesis when the
  chain already produced a confident answer).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import structlog

from core.budgets import BudgetManager
from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)


@dataclass
class ChainStep:
    name: str
    prompt_template: str
    output_key: str
    temperature: float = 0.0
    max_tokens: int = 1024
    transform: Callable[[str], Any] | None = None
    stop_if: Callable[[dict[str, Any]], bool] | None = None


class PromptChain:
    """
    Prompt Chaining Workflow.

    Example usage for Ask-the-Web:
        Step 1: Identify key entities in the query
        Step 2: Generate optimized search queries for those entities
        Step 3: (search happens externally) → Step 4: Draft the final answer
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        *,
        budget: BudgetManager | None = None,
    ) -> None:
        self._llm = llm_client
        self._model = model
        self._budget = budget
        self._steps: list[ChainStep] = []

    def add_step(self, step: ChainStep) -> "PromptChain":
        self._steps.append(step)
        return self  # fluent

    async def run(self, initial_context: dict[str, Any]) -> dict[str, Any]:
        context = dict(initial_context)
        logger.info("prompt_chain.start", num_steps=len(self._steps))

        for i, step in enumerate(self._steps, 1):
            if step.stop_if and step.stop_if(context):
                logger.info("prompt_chain.early_exit", step=step.name, n=i)
                break

            if self._budget is not None:
                self._budget.consume_step()

            logger.debug("prompt_chain.step", n=i, name=step.name)

            try:
                prompt = step.prompt_template.format(**context)
            except KeyError as exc:
                raise ValueError(
                    f"Step '{step.name}' template references missing key: {exc}"
                ) from exc

            response = await self._llm.complete(
                messages=[Message(role=Role.USER, content=prompt)],
                model=self._model,
                temperature=step.temperature,
                max_tokens=step.max_tokens,
                fast=True,  # chains are internal plumbing — cheap tier
                budget=self._budget,
            )

            raw = response.content or ""
            value = step.transform(raw) if step.transform else raw
            context[step.output_key] = value

            logger.debug(
                "prompt_chain.step_done",
                name=step.name,
                output_key=step.output_key,
                output_len=len(raw),
            )

        logger.info("prompt_chain.complete", keys=list(context.keys()))
        return context


def build_search_chain(
    llm_client: LLMClient,
    model: str | None = None,
    budget: BudgetManager | None = None,
) -> PromptChain:
    """
    Pre-built chain for the Ask-the-Web use case:
    query → intent analysis → search queries (search itself happens in
    the agent layer, which owns tool budgets).
    """
    def parse_queries(text: str) -> list[str]:
        text = text.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(q) for q in parsed][:5]
            except json.JSONDecodeError:
                pass
        return [line.strip("- ").strip() for line in text.splitlines()
                if line.strip()][:5]

    chain = PromptChain(llm_client, model, budget=budget)

    chain.add_step(ChainStep(
        name="identify_intent",
        prompt_template=(
            "Analyze this user question and identify:\n"
            "1. The main intent (factual, opinion, how-to, comparison, etc.)\n"
            "2. Key entities or concepts\n"
            "3. Time sensitivity (real-time vs historical)\n\n"
            "Question: {query}\n\n"
            "Respond concisely in 3 labeled lines."
        ),
        output_key="intent_analysis",
        temperature=0.0,
        max_tokens=256,
    ))

    chain.add_step(ChainStep(
        name="generate_search_queries",
        prompt_template=(
            "Based on this intent analysis, generate 3 optimized web search queries.\n\n"
            "Original question: {query}\n"
            "Intent analysis: {intent_analysis}\n\n"
            "Return a JSON array of search query strings only. No explanation."
        ),
        output_key="search_queries",
        temperature=0.0,
        max_tokens=256,
        transform=parse_queries,
    ))

    return chain
