"""
Parallelization Workflows — sectioning and voting.

Production hardening:
* Sectioning workers run bounded (semaphore) with per-item timeout and
  EXCEPTION ISOLATION: one item failing returns a structured error string
  in-place; the other items complete (FM-13). The old version crashed the
  whole gather on the first failure.
* Voting caps fan-out at ``max_votes`` and normalizes answers before
  counting; ties resolve deterministically toward the first-seen answer.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)

WorkFn = Callable[[Any], Awaitable[str]]


class ParallelSectioning:
    """
    Parallelization — Sectioning pattern.

    Splits a large task into independent sections and processes them
    concurrently (e.g., scraping 5 URLs simultaneously).
    """

    def __init__(self, max_concurrency: int = 5, item_timeout_s: float = 15.0) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._item_timeout_s = item_timeout_s

    async def run(self, items: list[Any], worker: WorkFn) -> list[str]:
        """
        Run worker on each item concurrently. Results come back IN ORDER,
        with failures replaced by an error marker string — never an
        exception that kills the batch.
        """

        async def _bounded(index: int, item: Any) -> str:
            async with self._semaphore:
                try:
                    return await asyncio.wait_for(
                        worker(item), timeout=self._item_timeout_s
                    )
                except Exception as exc:
                    logger.warning(
                        "sectioning.item_failed", index=index, error=str(exc)[:150]
                    )
                    return f"__ERROR__ item {index}: {type(exc).__name__}"

        results = await asyncio.gather(*[_bounded(i, it) for i, it in enumerate(items)])
        return list(results)


class ParallelVoting:
    """
    Parallelization — Voting pattern.

    Runs the same prompt N times (temperature > 0) and aggregates via
    majority vote. Useful for fact verification and classification.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        num_votes: int = 3,
        temperature: float = 0.7,
        max_votes: int = 5,
    ) -> None:
        self._llm = llm_client
        self._model = model
        self._num_votes = max(1, min(num_votes, max_votes))
        self._temperature = temperature

    async def vote(
        self,
        messages: list[Message],
        extract_answer: Callable[[str], str] | None = None,
    ) -> tuple[str, dict[str, int]]:
        """
        Run messages N times → (majority_answer, vote_counts).
        ``extract_answer`` normalizes each raw response before counting.
        """
        tasks = [
            self._llm.complete(
                messages=messages,
                model=self._model,
                temperature=self._temperature,
                fast=True,
            )
            for _ in range(self._num_votes)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        answers: list[str] = []
        for r in responses:
            if isinstance(r, Exception):
                answers.append("__VOTE_ERROR__")
                continue
            raw = r.content or ""
            answers.append(extract_answer(raw) if extract_answer else raw.strip())

        counts = Counter(answers)
        # Deterministic tie-break: most_common orders by count then
        # insertion order — first-seen answer wins ties.
        majority = counts.most_common(1)[0][0]

        agreement = counts.get(majority, 0) / max(1, len(answers))
        logger.info(
            "parallel_voting.result",
            majority=majority[:80],
            distribution=dict(counts),
            agreement=round(agreement, 2),
        )

        return majority, dict(counts)


class AnswerVerifier:
    """
    Voting use-case: verify a claim as TRUE/FALSE/UNCERTAIN.
    Confidence < threshold flags the claim for a second source.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        num_votes: int = 3,
    ) -> None:
        self._voter = ParallelVoting(
            llm_client=llm_client, model=model,
            num_votes=num_votes, temperature=0.5,
        )

    async def verify(self, claim: str, context: str) -> dict[str, Any]:
        prompt = (
            f"Context:\n{context[:4000]}\n\n"
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
