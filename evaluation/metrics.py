from __future__ import annotations

import re
from typing import Any


class TextMetrics:
    """
    Lightweight text quality metrics that run without an LLM.
    Used as fast pre-filters before expensive LLM evaluation.
    """

    @staticmethod
    def citation_coverage(answer: str, sources: list[dict[str, str]]) -> float:
        """
        What fraction of provided sources are actually cited in the answer?
        Citations detected as [Source N], [1], or bare URL presence.
        """
        if not sources:
            return 1.0  # No sources required

        cited = 0
        answer_lower = answer.lower()

        for i, src in enumerate(sources, 1):
            url = src.get("url", "")
            domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]

            if (
                f"[source {i}]" in answer_lower
                or f"[{i}]" in answer
                or domain in answer_lower
                or url in answer
            ):
                cited += 1

        return cited / len(sources)

    @staticmethod
    def answer_length_score(answer: str, min_words: int = 50, max_words: int = 800) -> float:
        """
        Penalizes answers that are too short or too long.
        Returns 1.0 for answers in [min_words, max_words] range.
        """
        words = len(answer.split())
        if words < min_words:
            return words / min_words
        if words > max_words:
            return max(0.5, max_words / words)
        return 1.0

    @staticmethod
    def has_structure(answer: str) -> float:
        """
        Checks if the answer uses markdown structure (headers, lists).
        Score: 0.0 = plain text, 1.0 = well-structured.
        """
        score = 0.0
        if re.search(r"^#{1,3} .+", answer, re.MULTILINE):
            score += 0.4  # Has headers
        if re.search(r"^[-*] .+", answer, re.MULTILINE):
            score += 0.3  # Has bullet list
        if re.search(r"^\d+\. .+", answer, re.MULTILINE):
            score += 0.3  # Has numbered list
        return min(1.0, score)

    @staticmethod
    def sources_section_present(answer: str) -> bool:
        """Check if answer ends with a Sources section."""
        return bool(re.search(
            r"#{1,3}\s*sources?\s*\n", answer, re.IGNORECASE
        ))

    @staticmethod
    def compute_all(
        answer: str,
        sources: list[dict[str, str]],
    ) -> dict[str, float]:
        return {
            "citation_coverage": TextMetrics.citation_coverage(answer, sources),
            "length_score": TextMetrics.answer_length_score(answer),
            "structure_score": TextMetrics.has_structure(answer),
            "has_sources_section": float(TextMetrics.sources_section_present(answer)),
        }