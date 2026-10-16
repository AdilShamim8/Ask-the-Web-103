from __future__ import annotations

from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger(__name__)


class TextSummarizerTool(BaseTool):
    """
    Summarizes long text content into a concise form.
    This is an internal tool invoked by the agent without an LLM call,
    using simple extractive summarization as a lightweight fallback.
    For production, swap _extractive_summarize with an LLM call.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="summarize_text",
            description=(
                "Summarize a long piece of text into key points. "
                "Useful after scraping a webpage to condense the content."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text content to summarize",
                    },
                    "max_sentences": {
                        "type": "integer",
                        "description": "Maximum number of sentences in the summary",
                        "default": 5,
                    },
                },
                "required": ["text"],
            },
        )

    async def execute(
        self, text: str, max_sentences: int = 5, **_: Any
    ) -> str:
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]

        if len(sentences) <= max_sentences:
            return ". ".join(sentences) + "."

        # Simple extractive: pick first, last, and evenly spaced middle sentences
        step = max(1, len(sentences) // max_sentences)
        selected = sentences[::step][:max_sentences]
        return ". ".join(selected) + "."