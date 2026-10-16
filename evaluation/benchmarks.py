from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from agents import AgentType, build_agent
from evaluation.evaluator import AnswerEvaluator
from core.llm_client import LLMClient

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkCase:
    id: str
    query: str
    ground_truth: str | None = None
    expected_keywords: list[str] = field(default_factory=list)
    category: str = "general"


@dataclass
class BenchmarkResult:
    case_id: str
    query: str
    answer: str
    overall_score: float
    scores: dict[str, float]
    passed: bool
    latency_s: float
    iterations: int
    tools_called: list[str]
    category: str


class BenchmarkRunner:
    """
    Runs a suite of test cases through the agent and collects
    performance + quality metrics. Use in CI or for regression testing.
    """

    # Built-in benchmark cases
    DEFAULT_CASES = [
        BenchmarkCase(
            id="factual_01",
            query="What is the current population of Tokyo?",
            expected_keywords=["million", "tokyo", "population"],
            category="factual",
        ),
        BenchmarkCase(
            id="research_01",
            query="What are the main differences between RAG and fine-tuning for LLMs?",
            expected_keywords=["retrieval", "fine-tuning", "context", "training"],
            category="research",
        ),
        BenchmarkCase(
            id="calc_01",
            query="What is the compound interest on $10,000 at 5% annual rate for 10 years?",
            ground_truth="$16,288.95",
            expected_keywords=["16,288", "compound", "interest"],
            category="calculation",
        ),
        BenchmarkCase(
            id="multi_01",
            query=(
                "Compare the GDP, population, and tech industry size "
                "of the United States and China in 2024."
            ),
            expected_keywords=["gdp", "population", "united states", "china"],
            category="multi_faceted",
        ),
        BenchmarkCase(
            id="current_01",
            query="What are the latest developments in quantum computing?",
            expected_keywords=["qubit", "quantum", "error correction"],
            category="current_events",
        ),
    ]

    def __init__(
        self,
        agent_type: AgentType = AgentType.REACT,
        model: str | None = None,
    ) -> None:
        self._agent_type = agent_type
        self._model = model
        self._evaluator = AnswerEvaluator(llm_client=LLMClient(), model=model)

    async def run_case(self, case: BenchmarkCase) -> BenchmarkResult:
        log = logger.bind(case_id=case.id, category=case.category)
        log.info("benchmark.case.start")

        start = time.perf_counter()
        agent = build_agent(self._agent_type, model=self._model)

        try:
            state = await agent.run(case.query)
            latency = time.perf_counter() - start
            answer = state.final_answer or ""

            eval_result = await self._evaluator.evaluate(
                query=case.query,
                answer=answer,
                sources=state.sources,
                ground_truth=case.ground_truth,
            )

            # Keyword presence bonus
            answer_lower = answer.lower()
            keyword_hits = sum(
                1 for kw in case.expected_keywords if kw.lower() in answer_lower
            )
            keyword_score = (
                keyword_hits / len(case.expected_keywords)
                if case.expected_keywords else 1.0
            )

            overall = min(1.0, eval_result["overall_score"] * 0.8 + keyword_score * 0.2)

            log.info(
                "benchmark.case.done",
                overall=round(overall, 3),
                latency_s=round(latency, 2),
            )

            return BenchmarkResult(
                case_id=case.id,
                query=case.query,
                answer=answer,
                overall_score=overall,
                scores=eval_result["scores"],
                passed=overall >= 0.70,
                latency_s=round(latency, 2),
                iterations=state.iterations,
                tools_called=[tc.name for tc in state.tool_calls_made],
                category=case.category,
            )

        except Exception as exc:
            latency = time.perf_counter() - start
            log.error("benchmark.case.failed", error=str(exc))
            return BenchmarkResult(
                case_id=case.id,
                query=case.query,
                answer=f"ERROR: {exc}",
                overall_score=0.0,
                scores={},
                passed=False,
                latency_s=round(latency, 2),
                iterations=0,
                tools_called=[],
                category=case.category,
            )

    async def run_all(
        self,
        cases: list[BenchmarkCase] | None = None,
        concurrency: int = 2,
    ) -> dict[str, Any]:
        cases = cases or self.DEFAULT_CASES
        sem = asyncio.Semaphore(concurrency)

        async def _bounded(case: BenchmarkCase) -> BenchmarkResult:
            async with sem:
                return await self.run_case(case)

        results = list(
            await asyncio.gather(*[_bounded(c) for c in cases])
        )

        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.overall_score for r in results) / total
        avg_latency = sum(r.latency_s for r in results) / total

        by_category: dict[str, list[float]] = {}
        for r in results:
            by_category.setdefault(r.category, []).append(r.overall_score)

        category_scores = {
            cat: round(sum(scores) / len(scores), 3)
            for cat, scores in by_category.items()
        }

        summary = {
            "total_cases": total,
            "passed": passed,
            "pass_rate": round(passed / total, 3),
            "avg_score": round(avg_score, 3),
            "avg_latency_s": round(avg_latency, 2),
            "category_scores": category_scores,
            "results": [
                {
                    "case_id": r.case_id,
                    "category": r.category,
                    "overall_score": r.overall_score,
                    "passed": r.passed,
                    "latency_s": r.latency_s,
                    "iterations": r.iterations,
                }
                for r in results
            ],
        }

        logger.info(
            "benchmark.summary",
            pass_rate=summary["pass_rate"],
            avg_score=summary["avg_score"],
            avg_latency_s=summary["avg_latency_s"],
        )

        return summary