"""
Base agent — shared machinery for every reasoning strategy.

Production additions:
* Request-scoped ``BudgetManager`` + ``UsageTracker`` are created here and
  threaded to every LLM/tool call (ADR-005). A strategy that forgets to
  check them is still protected because executor/LLMClient enforce.
* Telemetry: AGENT_RUNS/AGENT_LATENCY counters with outcome labels;
  budget exhaustion is an EXPECTED outcome, not an error (FM-06).
* Graceful degradation markers on state: ``degraded`` +
  ``degradation_reasons`` let the API disclose quality loss honestly.
"""

from __future__ import annotations

import abc
import time
from typing import Any, AsyncIterator

import structlog

from configs.settings import get_settings
from core.budgets import BudgetConfig, BudgetManager
from core.exceptions import BudgetExceededError, ContextWindowExceededError, MaxIterationsExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role
from core.observability import AGENT_LATENCY, AGENT_RUNS, BUDGET_EXCEEDED
from core.token_counter import TokenCounter
from core.usage_tracker import UsageTracker
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

    agent_name: str = "base"

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        *,
        budget: BudgetManager | None = None,
        usage: UsageTracker | None = None,
    ) -> None:
        self._llm = llm_client
        self._registry = registry
        self._executor = executor
        self._settings = get_settings()
        self._model = model or self._settings.default_model
        self._max_iterations = max_iterations or self._settings.max_agent_iterations
        self._system_prompt = system_prompt
        self._budget = budget or BudgetManager(BudgetConfig.from_settings())
        self._usage = usage or UsageTracker()

    @abc.abstractmethod
    async def run(self, query: str, **kwargs: Any) -> AgentState:
        """Run the agent and return final AgentState."""
        ...

    # ── Shared helpers ───────────────────────────────────────────────────

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
        """Keep message history within the context window."""
        trimmed = TokenCounter.trim_to_fit(
            messages=state.messages,
            model=self._model,
            context_limit=self._settings.context_window_limit,
            reserved_for_response=self._settings.max_tokens_per_response,
        )
        if len(trimmed) < len(state.messages):
            dropped = len(state.messages) - len(trimmed)
            logger.warning(
                "context.trimmed", dropped_messages=dropped, model=self._model,
            )
        state.messages = trimmed

    def _extract_sources(self, state: AgentState) -> None:
        """Parse tool results for URLs; build deduplicated sources list."""
        import json

        seen: set[str] = set()
        for tr in state.tool_results_received:
            if tr.tool_name not in ("web_search", "scrape_webpage"):
                continue
            try:
                data = json.loads(tr.content)
            except (json.JSONDecodeError, TypeError):
                continue

            if "results" in data:
                for r in data["results"]:
                    url = r.get("url", "")
                    title = r.get("title", url)
                    if url and url not in seen:
                        seen.add(url)
                        state.sources.append({"title": title, "url": url})

            if "url" in data and data["url"] not in seen:
                seen.add(data["url"])
                state.sources.append({"title": data["url"], "url": data["url"]})

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        return self._registry.get_schemas()

    def _finish(self, state: AgentState, start: float, outcome: str = "ok") -> None:
        """Shared teardown: attach usage/budget, emit telemetry, log."""
        state.metadata["usage"] = self._usage.to_dict()
        state.metadata["budget"] = self._budget.snapshot().to_dict()

        AGENT_RUNS.labels(agent_type=self.agent_name, outcome=outcome).inc()
        AGENT_LATENCY.labels(agent_type=self.agent_name).observe(
            time.perf_counter() - start
        )
        self._usage.export_cost_metric()

        logger.info(
            f"{self.agent_name}.completed",
            query=state.query[:80],
            iterations=state.iterations,
            tools_called=len(state.tool_calls_made),
            sources_found=len(state.sources),
            elapsed_s=round(time.perf_counter() - start, 2),
            cost_usd=round(self._usage.report.total_cost_usd, 6),
            degraded=state.degraded,
        )

    def _mark_budget_exceeded(self, state: AgentState, exc: BudgetExceededError) -> None:
        """Budget exhaustion is a controlled outcome (FM-06): mark, emit,
        and attach a best-effort partial answer."""
        BUDGET_EXCEEDED.labels(dimension=exc.dimension).inc()
        state.degraded = True
        state.degradation_reasons.append(f"budget:{exc.dimension}")
        state.metadata["budget_exceeded"] = exc.to_dict()
        if state.final_answer is None:
            state.final_answer = self._partial_answer(state)

    @staticmethod
    def _partial_answer(state: AgentState) -> str:
        """Best-effort answer from evidence already gathered."""
        snippets: list[str] = []
        for tr in state.tool_results_received[:3]:
            if not tr.is_error and tr.tool_name == "web_search":
                snippets.append(tr.content[:600])
        if snippets:
            return (
                "I was unable to complete the full research within this "
                "request's budget. Preliminary sources found:\n\n"
                + "\n\n".join(f"- {s}" for s in snippets)
                + "\n\n_Partial answer — request terminated by budget guard._"
            )
        return (
            "This request exceeded its processing budget before an answer "
            "could be produced. Please try a narrower question."
        )

    # Kept for backward compatibility with older call sites.
    def _log_state_summary(self, state: AgentState, elapsed: float) -> None:
        self._finish(state, elapsed)
