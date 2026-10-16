from __future__ import annotations

import json
from typing import Any

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role
from evaluation.metrics import TextMetrics

logger = structlog.get_logger(__name__)

_EVAL_PROMPT = """\
You are an expert evaluator for AI-generated research answers.

Evaluate the answer below on a scale of 0.0 to 1.0 for each dimension.

QUESTION: {query}

ANSWER:
{answer}

SOURCES PROVIDED:
{sources}

{ground_truth_section}

Evaluate these dimensions:
1. factual_accuracy    — Are claims factually correct and well-supported?
2. completeness        — Does it fully address all aspects of the question?
3. clarity             — Is it clearly written and easy to understand?
4. source_usage        — Are sources appropriately cited and relevant?
5. hallucination_risk  — How likely is the answer to contain hallucinations?
                          (0.0 = definitely hallucinated, 1.0 = clearly grounded)

Return ONLY a JSON object like:
{{
  "factual_accuracy": 0.85,
  "completeness": 0.90,
  "clarity": 0.95,
  "source_usage": 0.80,
  "hallucination_risk": 0.88,
  "feedback": {{
    "factual_accuracy": "one sentence of feedback",
    "completeness": "one sentence of feedback",
    "clarity": "one sentence of feedback",
    "source_usage": "one sentence of feedback",
    "hallucination_risk": "one sentence of feedback"
  }}
}}
"""

_PASS_THRESHOLD = 0.70


class AnswerEvaluator:
    """
    Multi-dimensional answer evaluator combining:
    - Fast rule-based text metrics (no LLM cost)
    - LLM-based semantic evaluation
    - Optional ground truth comparison
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        pass_threshold: float = _PASS_THRESHOLD,
    ) -> None:
        self._llm = llm_client
        self._model = model
        self._threshold = pass_threshold

    async def evaluate(
        self,
        query: str,
        answer: str,
        sources: list[dict[str, str]] | None = None,
        ground_truth: str | None = None,
    ) -> dict[str, Any]:
        sources = sources or []

        # ── Fast metrics ──────────────────────────────────────────────────
        text_scores = TextMetrics.compute_all(answer, sources)

        # ── LLM evaluation ────────────────────────────────────────────────
        llm_scores, llm_feedback = await self._llm_evaluate(
            query, answer, sources, ground_truth
        )

        # ── Merge scores ──────────────────────────────────────────────────
        all_scores = {**text_scores, **llm_scores}

        # Weighted overall score
        weights = {
            "factual_accuracy": 0.30,
            "completeness": 0.20,
            "clarity": 0.15,
            "source_usage": 0.15,
            "hallucination_risk": 0.20,
        }
        overall = sum(
            all_scores.get(k, 0.5) * w
            for k, w in weights.items()
        )

        # Bonus for structural quality
        structure_bonus = text_scores.get("structure_score", 0) * 0.05
        overall = min(1.0, overall + structure_bonus)

        passed = overall >= self._threshold

        logger.info(
            "evaluator.result",
            query=query[:60],
            overall=round(overall, 3),
            passed=passed,
        )

        return {
            "scores": {k: round(v, 3) for k, v in all_scores.items()},
            "feedback": llm_feedback,
            "overall_score": round(overall, 3),
            "passed": passed,
        }

    async def _llm_evaluate(
        self,
        query: str,
        answer: str,
        sources: list[dict[str, str]],
        ground_truth: str | None,
    ) -> tuple[dict[str, float], dict[str, str]]:
        sources_text = "\n".join(
            f"- [{i}] {s.get('title', '')} ({s.get('url', '')})"
            for i, s in enumerate(sources, 1)
        ) or "No sources provided."

        ground_truth_section = ""
        if ground_truth:
            ground_truth_section = (
                f"\nGROUND TRUTH (correct answer for reference):\n{ground_truth}\n"
            )

        prompt = _EVAL_PROMPT.format(
            query=query,
            answer=answer[:3000],
            sources=sources_text,
            ground_truth_section=ground_truth_section,
        )

        response = await self._llm.complete(
            messages=[Message(role=Role.USER, content=prompt)],
            model=self._model,
            temperature=0.0,
            max_tokens=512,
        )

        raw = (response.content or "").strip()
        return self._parse_eval_response(raw)

    def _parse_eval_response(
        self, raw: str
    ) -> tuple[dict[str, float], dict[str, str]]:
        try:
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            data = json.loads(raw)

            scores = {
                k: float(data.get(k, 0.5))
                for k in (
                    "factual_accuracy", "completeness",
                    "clarity", "source_usage", "hallucination_risk"
                )
            }
            feedback = data.get("feedback", {})
            return scores, feedback

        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("evaluator.parse_failed", raw=raw[:200])
            default_scores = {
                "factual_accuracy": 0.5,
                "completeness": 0.5,
                "clarity": 0.5,
                "source_usage": 0.5,
                "hallucination_risk": 0.5,
            }
            return default_scores, {}