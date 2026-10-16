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

    # ── Grounding metrics (production additions) ──────────────────────
    # citation_coverage measures recall: of sources given, how many are
    # cited. The failure that actually burns users is the INVERSE: the
    # answer cites things that don't exist (fabricated citations).
    # That's precision.

    _CITATION_RE = re.compile(r"\[(?:source\s+)?(\d+)\]", re.IGNORECASE)
    _URL_RE = re.compile(r"https?://[^\s\)\]\>]+")

    @staticmethod
    def citation_precision(answer: str, sources: list[dict[str, str]]) -> float:
        """
        Fraction of citation markers in the answer that point to a REAL
        source. [1] with fewer than 1 sources = fabricated → 0.0.
        """
        markers = TextMetrics._CITATION_RE.findall(answer)
        if not markers:
            # Bare URLs count as citations too.
            urls = TextMetrics._URL_RE.findall(answer)
            if not urls:
                return 1.0  # nothing cited, nothing fabricated
            known = {s.get("url", "") for s in sources}
            hits = sum(1 for u in urls if u.rstrip("/.") in known)
            return hits / len(urls) if urls else 1.0

        valid = sum(1 for n in markers if 1 <= int(n) <= len(sources))
        return valid / len(markers)

    @staticmethod
    def unsupported_citation_rate(answer: str, sources: list[dict[str, str]]) -> float:
        """Complement of citation_precision — the fabrication rate."""
        return round(1.0 - TextMetrics.citation_precision(answer, sources), 3)

    @staticmethod
    def compute_all(
        answer: str,
        sources: list[dict[str, str]],
    ) -> dict[str, float]:
        return {
            "citation_coverage": TextMetrics.citation_coverage(answer, sources),
            "citation_precision": TextMetrics.citation_precision(answer, sources),
            "unsupported_citation_rate": TextMetrics.unsupported_citation_rate(
                answer, sources
            ),
            "length_score": TextMetrics.answer_length_score(answer),
            "structure_score": TextMetrics.has_structure(answer),
            "has_sources_section": float(TextMetrics.sources_section_present(answer)),
        }