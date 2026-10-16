from __future__ import annotations

import abc
import time
from typing import Any, AsyncIterator

import structlog

from configs.settings import get_settings
from core.exceptions import ContextWindowExceededError, MaxIterationsExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from core.token_counter import TokenCounter
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """\
You are a world-class research assistant similar to Perplexity AI.
Your job is to answer the user's question accurately using real-time web information.

CAPABILITIES:
- You have access to tools: web_search, scrape_webpage, calculator, summarize_text
- You can call multiple tools in sequence or in parallel
- You reason step-by-step before acting

RULES:
1. Always search the web before answering factual or time-sensitive questions
2. Cite your sources using [Source N] notation referencing URLs
3. If the first search doesn't give enough information, search again with a refined query
4. Never fabricate facts — only state what you found
5. Structure your final answer clearly with headers when appropriate
6. If a calculation is needed, use the calculator tool — never compute in your head

OUTPUT FORMAT:
- Use markdown for structure
- End with a "Sources" section listing all URLs referenced
- Keep the answer concise but complete
"""


class BaseAgent(abc.ABC):
    """
    Abstract base agent.
    Subclasses implement `run` with their specific reasoning strategy.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._llm = llm_client
        self._registry = registry
        self._executor = executor
        self._settings = get_settings()
        self._model = model or self._settings.default_model
        self._max_iterations = max_iterations or self._settings.max_agent_iterations
        self._system_prompt = system_prompt

    @abc.abstractmethod
    async def run(self, query: str, **kwargs: Any) -> AgentState:
        """Run the agent and return final AgentState."""
        ...

    def _build_initial_state(self, query: str) -> AgentState:
        state = AgentState(query=query)
        state.messages.append(
            Message(role=Role.SYSTEM, content=self._system_prompt)
        )
        state.messages.append(
            Message(role=Role.USER, content=query)
        )
        return state

    def _check_iterations(self, state: AgentState) -> None:
        if state.iterations >= self._max_iterations:
            raise MaxIterationsExceededError(
                f"Agent exceeded {self._max_iterations} iterations "
                f"without reaching a final answer."
            )

    def _trim_context(self, state: AgentState) -> None:
        """Ensure message history stays within context window."""
        trimmed = TokenCounter.trim_to_fit(
            messages=state.messages,
            model=self._model,
            context_limit=self._settings.context_window_limit,
            reserved_for_response=self._settings.max_tokens_per_response,
        )
        if len(trimmed) < len(state.messages):
            dropped = len(state.messages) - len(trimmed)
            logger.warning(
                "context.trimmed",
                dropped_messages=dropped,
                model=self._model,
            )
        state.messages = trimmed

    def _extract_sources(self, state: AgentState) -> None:
        """
        Parse tool results for URLs and build a deduplicated sources list.
        """
        import json
        seen: set[str] = set()

        for tr in state.tool_results_received:
            if tr.tool_name not in ("web_search", "scrape_webpage"):
                continue
            try:
                data = json.loads(tr.content)
            except (json.JSONDecodeError, TypeError):
                continue

            # web_search results
            if "results" in data:
                for r in data["results"]:
                    url = r.get("url", "")
                    title = r.get("title", url)
                    if url and url not in seen:
                        seen.add(url)
                        state.sources.append({"title": title, "url": url})

            # scrape_webpage result
            if "url" in data and data["url"] not in seen:
                seen.add(data["url"])
                state.sources.append({"title": data["url"], "url": data["url"]})

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        return self._registry.get_schemas()

    def _log_state_summary(self, state: AgentState, elapsed: float) -> None:
        logger.info(
            "agent.completed",
            query=state.query[:80],
            iterations=state.iterations,
            tools_called=len(state.tool_calls_made),
            sources_found=len(state.sources),
            elapsed_s=round(elapsed, 2),
            has_answer=state.final_answer is not None,
        )