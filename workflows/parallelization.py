from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, TypeVar

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)

T = TypeVar("T")
WorkFn = Callable[[Any], Awaitable[str]]


class ParallelSectioning:
    """
    Parallelization — Sectioning pattern.

    Splits a large task into independent sections and processes them
    concurrently. Example: scraping 5 URLs simultaneously.
    """

    def __init__(self, max_concurrency: int = 5) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(
        self,
        items: list[Any],
        worker: WorkFn,
    ) -> list[str]:
        """Run worker on each item concurrently. Returns results in order."""
        async def _bounded(item: Any) -> str:
            async with self._semaphore:
                return await worker(item)

        results = await asyncio.gather(*[_bounded(item) for item in items])
        return list(results)


class ParallelVoting:
    """
    Parallelization — Voting pattern.

    Runs the same prompt through the LLM N times (with temperature > 0)
    and aggregates responses via majority vote.
    Useful for: fact verification, classification, answer reliability.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        num_votes: int = 3,
        temperature: float = 0.7,
    ) -> None:
        self._llm = llm_client
        self._model = model
        self._num_votes = num_votes
        self._temperature = temperature

    async def vote(
        self,
        messages: list[Message],
        extract_answer: Callable[[str], str] | None = None,
    ) -> tuple[str, dict[str, int]]:
        """
        Run messages N times and return (majority_answer, vote_counts).
        extract_answer: optional fn to normalize each raw response.
        """
        tasks = [
            self._llm.complete(
                messages=messages,
                model=self._model,
                temperature=self._temperature,
            )
            for _ in range(self._num_votes)
        ]
        responses = await asyncio.gather(*tasks)

        answers: list[str] = []
        for r in responses:
            raw = r.content or ""
            normalized = extract_answer(raw) if extract_answer else raw.strip()
            answers.append(normalized)

        counts = Counter(answers)
        majority = counts.most_common(1)[0][0]

        logger.info(
            "parallel_voting.result",
            majority=majority[:80],
            distribution=dict(counts),
        )

        return majority, dict(counts)


class AnswerVerifier:
    """
    Specialized voting use-case: verify if a claim is true/false/uncertain
    by asking the LLM multiple times.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        num_votes: int = 3,
    ) -> None:
        self._voter = ParallelVoting(
            llm_client=llm_client,
            model=model,
            num_votes=num_votes,
            temperature=0.5,
        )

    async def verify(self, claim: str, context: str) -> dict[str, Any]:
        prompt = (
            f"Context:\n{context}\n\n"
            f"Claim: {claim}\n\n"
            "Based solely on the context, is this claim TRUE, FALSE, or UNCERTAIN?\n"
            "Respond with exactly one word: TRUE, FALSE, or UNCERTAIN."
        )

        def extract(text: str) -> str:
            text = text.strip().upper()
            for verdict in ("TRUE", "FALSE", "UNCERTAIN"):
                if verdict in text:
                    return verdict
            return "UNCERTAIN"

        majority, distribution = await self._voter.vote(
            messages=[Message(role=Role.USER, content=prompt)],
            extract_answer=extract,
        )

        total = sum(distribution.values())
        confidence = distribution.get(majority, 0) / total

        return {
            "verdict": majority,
            "confidence": round(confidence, 2),
            "distribution": distribution,
            "claim": claim,
        }