from __future__ import annotations

from typing import Any

import structlog

from core.llm_client import LLMClient
from core.message_types import Message, Role

logger = structlog.get_logger(__name__)

_SELF_CRITIQUE_PROMPT = """\
Review the following answer for the given question.
Identify any factual gaps, logical errors, or missing information.

QUESTION: {question}
ANSWER: {answer}

List specific issues as bullet points. If the answer is perfect, write "No issues found."
"""

_IMPROVEMENT_PROMPT = """\
Improve the following answer based on the critique provided.

QUESTION: {question}
ORIGINAL ANSWER: {answer}
CRITIQUE: {critique}

Write an improved answer that addresses all critique points.
"""


class ReflectionWorkflow:
    """
    Standalone Reflection workflow (not tied to an agent).
    Can be used as a post-processing step on any generated text.

    Steps:
        1. Generate initial answer
        2. Self-critique the answer
        3. Revise the answer based on critique
        4. Optionally repeat for `rounds` iterations
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str | None = None,
        rounds: int = 1,
    ) -> None:
        self._llm = llm_client
        self._model = model
        self._rounds = rounds

    async def run(
        self,
        question: str,
        initial_answer: str,
    ) -> dict[str, Any]:
        """
        Returns:
            {
                "final_answer": str,
                "rounds": [{"critique": str, "revised_answer": str}],
            }
        """
        answer = initial_answer
        history: list[dict[str, str]] = []

        for round_num in range(self._rounds):
            logger.debug("reflection.round", n=round_num + 1)

            # Step 1: Critique
            critique_response = await self._llm.complete(
                messages=[
                    Message(
                        role=Role.USER,
                        content=_SELF_CRITIQUE_PROMPT.format(
                            question=question, answer=answer
                        ),
                    )
                ],
                model=self._model,
                temperature=0.0,
                max_tokens=512,
            )
            critique = critique_response.content or ""

            if "no issues found" in critique.lower():
                logger.info("reflection.no_issues", round=round_num + 1)
                history.append({"critique": critique, "revised_answer": answer})
                break

            # Step 2: Improve
            improve_response = await self._llm.complete(
                messages=[
                    Message(
                        role=Role.USER,
                        content=_IMPROVEMENT_PROMPT.format(
                            question=question,
                            answer=answer,
                            critique=critique,
                        ),
                    )
                ],
                model=self._model,
                temperature=0.1,
                max_tokens=self._llm._settings.max_tokens_per_response,
            )
            answer = improve_response.content or answer
            history.append({"critique": critique, "revised_answer": answer})

        return {"final_answer": answer, "rounds": history}