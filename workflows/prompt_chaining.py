from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)

# A step is an async function that takes context and returns updated context
StepFn = Callable[[dict[str, Any], LLMClient], Awaitable[dict[str, Any]]]


@dataclass
class ChainStep:
    name: str
    prompt_template: str
    output_key: str
    temperature: float = 0.0
    max_tokens: int = 1024
    transform: Callable[[str], Any] | None = None


class PromptChain:
    """
    Prompt Chaining Workflow.

    Each step:
        1. Formats its prompt using the context (outputs from prior steps)
        2. Calls the LLM
        3. Stores its output in the context under `output_key`

    Example usage for Ask-the-Web:
        Step 1: Identify key entities in the query
        Step 2: Generate optimized search queries for those entities
        Step 3: Summarize search results
        Step 4: Draft the final answer
    """

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model
        self._steps: list[ChainStep] = []

    def add_step(self, step: ChainStep) -> "PromptChain":
        self._steps.append(step)
        return self  # fluent

    async def run(self, initial_context: dict[str, Any]) -> dict[str, Any]:
        context = dict(initial_context)
        logger.info("prompt_chain.start", num_steps=len(self._steps))

        for i, step in enumerate(self._steps, 1):
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


def build_search_chain(llm_client: LLMClient, model: str | None = None) -> PromptChain:
    """
    Pre-built chain for the Ask-the-Web use case:
    query → search queries → (search happens externally) → final answer
    """
    import json

    def parse_queries(text: str) -> list[str]:
        text = text.strip()
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]

    chain = PromptChain(llm_client, model)

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