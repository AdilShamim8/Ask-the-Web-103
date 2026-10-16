"""
Tree Search Agent — beam search over reasoning paths.

Concept:
    - Root node = initial query
    - Expand    = LLM generates K candidate next thoughts
    - Score     = LLM rates each branch 0..1 (fast tier — it's a number)
    - Select    = keep top ``beam_width`` branches (beam search)
    - Terminate = a branch declares a final answer, or depth/budget ends

Production reality check (ADR-005, FM-07):
Tree search is the MOST expensive strategy in the catalog —
``depth × beam × branching`` LLM calls before a single answer. The old
version multiplied unconstrained: 4 × 2 × 3 × (expand + score) ≈ 24 calls.
This version:
* hard-caps the search envelope (branching ≤ 3, beam ≤ 2, depth ≤ 4)
* checks the shared budget before every expansion wave — the tree shrinks
  or stops when the request runs out of tokens/steps/time
* scoring runs on the fast model tier
* parallel waves are bounded and exception-isolated: one branch failing
  to expand must not kill the wave (FM-13)
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from agents.base_agent import BaseAgent
from core.exceptions import BudgetExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role, ToolCall, ToolResult
from tools.tool_executor import ToolExecutor
from tools.tool_registry import ToolRegistry

logger = structlog.get_logger(__name__)

_EXPAND_PROMPT = """\
You are reasoning step by step to answer: {query}

Current reasoning so far:
{history}

Generate {branching_factor} DISTINCT candidate next steps.
Each step should be a different approach or angle.
Format:
CANDIDATE 1: <thought and action>
CANDIDATE 2: <thought and action>
...
"""

_SCORE_PROMPT = """\
Rate how promising this reasoning path is for answering: {query}

Path so far:
{path}

Latest step: {candidate}

Score from 0.0 (completely wrong direction) to 1.0 (clearly on track).
Respond with ONLY a number like: 0.85
"""

_FINAL_PROMPT = """\
Based on this complete reasoning path, provide the final answer.

Question: {query}
Reasoning path:
{path}

Write a comprehensive final answer with sources.
"""

_CANDIDATE_RE = re.compile(r"CANDIDATE\s+\d+:\s*(.+)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+\.?\d*")


@dataclass
class TreeNode:
    thought: str
    messages: list[Message]
    score: float = 0.5
    depth: int = 0
    children: list[TreeNode] = field(default_factory=list)
    is_terminal: bool = False
    final_answer: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)


class TreeSearchAgent(BaseAgent):
    """
    Best-First / Beam Tree Search Agent with a hard cost envelope.
    """

    agent_name = "tree_search"

    # Search envelope caps — overriding these upward requires a budget
    # review (see ADR-005); they exist so a bad config can't 20× cost.
    MAX_BRANCHING = 3
    MAX_BEAM_WIDTH = 3
    MAX_DEPTH = 4

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        model: str | None = None,
        max_iterations: int | None = None,
        branching_factor: int = 3,
        max_depth: int = 4,
        beam_width: int = 2,
        **kwargs: Any,
    ) -> None:
        super().__init__(llm_client, registry, executor, model,
                         max_iterations, **kwargs)
        self._branching_factor = max(1, min(branching_factor, self.MAX_BRANCHING))
        self._max_depth = max(1, min(max_depth, self.MAX_DEPTH))
        self._beam_width = max(1, min(beam_width, self.MAX_BEAM_WIDTH))

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        state = self._build_initial_state(query)
        log = logger.bind(agent="TreeSearch", query=query[:60])
        log.info(
            "tree_search.start",
            branching=self._branching_factor,
            beam=self._beam_width,
            max_depth=self._max_depth,
        )

        try:
            root = TreeNode(
                thought="Starting search...",
                messages=list(state.messages),
                score=1.0,
                depth=0,
            )

            beam: list[TreeNode] = [root]
            best_terminal: TreeNode | None = None

            for depth in range(self._max_depth):
                # ── Budget gates before every wave ───────────────────
                self._budget.check_deadline()
                self._budget.consume_step()
                state.iterations += 1

                # Shrink the wave if the budget is running dry.
                if self._budget.would_exceed(input_tokens=2_000):
                    log.warning(
                        "tree_search.budget_low_shrinking",
                        remaining_s=round(self._budget.time_remaining_s(), 1),
                    )
                    self._beam_width = 1
                    self._branching_factor = 1

                log.debug("tree_search.depth", depth=depth, beam_size=len(beam))

                # ── Expand (exception-isolated per node) ─────────────
                expand_tasks = [self._expand_node(node, query) for node in beam]
                expanded_batches = await asyncio.gather(*expand_tasks, return_exceptions=True)

                next_candidates: list[TreeNode] = []
                for node, children in zip(beam, expanded_batches, strict=True):
                    if isinstance(children, BaseException):
                        log.warning(
                            "tree_search.expand_failed",
                            depth=depth, error=str(children)[:120],
                        )
                        continue  # one dead branch ≠ dead wave (FM-13)
                    node.children = children
                    next_candidates.extend(children)

                if not next_candidates:
                    break

                # ── Score in parallel (fast tier) ─────────────────────
                score_tasks = [self._score_node(node, query) for node in next_candidates]
                scores = await asyncio.gather(*score_tasks, return_exceptions=True)
                for node, score in zip(next_candidates, scores, strict=True):
                    node.score = 0.5 if isinstance(score, BaseException) else score

                # ── Terminal check ────────────────────────────────────
                terminals = [n for n in next_candidates if n.is_terminal]
                if terminals:
                    best_terminal = max(terminals, key=lambda n: n.score)
                    log.info("tree_search.terminal_found", score=best_terminal.score)
                    break

                next_candidates.sort(key=lambda n: n.score, reverse=True)
                beam = next_candidates[: self._beam_width]
                log.debug(
                    "tree_search.beam_selected",
                    top_scores=[round(n.score, 2) for n in beam],
                )

            # ── Extract final answer ──────────────────────────────────
            if best_terminal and best_terminal.final_answer:
                state.final_answer = best_terminal.final_answer
                state.tool_calls_made = best_terminal.tool_calls
                state.tool_results_received = best_terminal.tool_results
            else:
                best = max(beam, key=lambda n: n.score) if beam else root
                state.final_answer = await self._generate_final(best.messages, query)

        except BudgetExceededError as exc:
            log.warning("tree_search.budget_exceeded", dimension=exc.dimension)
            # Salvage: use whatever the current beam has gathered.
            # (renamed from `best` 2026-10-16: reusing the name forced a
            # TreeNode|None onto a variable mypy had already typed as
            # TreeNode from the happy path — and shadowed the semantic:
            # this is salvage, not the best node.)
            salvage = max(beam, key=lambda n: n.score) if beam else None
            if salvage is not None and salvage.tool_results:
                state.tool_calls_made = salvage.tool_calls
                state.tool_results_received = salvage.tool_results
            self._mark_budget_exceeded(state, exc)
            self._finish(state, start, outcome="budget_exceeded")
            return state

        self._extract_sources(state)
        self._finish(state, start)
        return state

    async def _expand_node(self, node: TreeNode, query: str) -> list[TreeNode]:
        """Generate branching_factor candidate children for a node."""
        history = "\n".join(
            f"- {m.content[:200]}"
            for m in node.messages
            if m.role == Role.ASSISTANT and m.content
        ) or "No steps yet."

        prompt = _EXPAND_PROMPT.format(
            query=query, history=history, branching_factor=self._branching_factor,
        )

        response = await self._llm.complete(
            messages=[Message(role=Role.USER, content=prompt)],
            model=self._model,
            temperature=0.8,  # higher temp for diverse candidates
            max_tokens=512,
            fast=True,
            budget=self._budget,
            usage_tracker=self._usage,
        )

        candidates = self._parse_candidates(response.content or "")

        children: list[TreeNode] = []
        for thought in candidates[: self._branching_factor]:
            tool_call, tool_result = await self._maybe_execute_tool(thought)

            child_messages = list(node.messages)
            child_messages.append(Message(role=Role.ASSISTANT, content=thought))

            is_terminal = self._is_final_answer(thought)
            final_answer = ""
            if is_terminal:
                final_answer = await self._generate_final(child_messages, query)

            children.append(TreeNode(
                thought=thought,
                messages=child_messages,
                depth=node.depth + 1,
                is_terminal=is_terminal,
                final_answer=final_answer,
                tool_calls=node.tool_calls + ([tool_call] if tool_call else []),
                tool_results=node.tool_results + ([tool_result] if tool_result else []),
            ))
        return children

    @staticmethod
    def _parse_candidates(text: str) -> list[str]:
        candidates = [
            m.group(1).strip()
            for m in (_CANDIDATE_RE.match(line) for line in text.splitlines())
            if m
        ]
        return candidates or [text.strip()]

    async def _score_node(self, node: TreeNode, query: str) -> float:
        """Score a branch's promise (fast tier — it's just a number)."""
        path = "\n".join(
            m.content[:200]
            for m in node.messages
            if m.role == Role.ASSISTANT and m.content
        ) or "Empty path"

        prompt = _SCORE_PROMPT.format(
            query=query, path=path, candidate=node.thought,
        )

        try:
            response = await self._llm.complete(
                messages=[Message(role=Role.USER, content=prompt)],
                model=self._model,
                temperature=0.0,
                max_tokens=10,
                fast=True,
                budget=self._budget,
                usage_tracker=self._usage,
            )
            raw = (response.content or "0.5").strip()
            match = _NUMBER_RE.search(raw)
            if not match:
                return 0.5
            return min(1.0, max(0.0, float(match.group())))
        except BudgetExceededError:
            raise
        except Exception:
            return 0.5  # scoring failure ≠ branch death

    @staticmethod
    def _is_final_answer(thought: str) -> bool:
        indicators = [
            "final answer", "in conclusion", "therefore,",
            "to summarize", "the answer is", "based on my research",
        ]
        lower = thought.lower()
        return any(ind in lower for ind in indicators)

    async def _maybe_execute_tool(
        self, thought: str
    ) -> tuple[ToolCall | None, ToolResult | None]:
        """Detect tool use described in a thought; execute it (guarded)."""
        for tool in self._registry.all_tools():
            if tool.name in thought.lower():
                query_match = re.search(r'"([^"]+)"', thought)
                if not query_match:
                    continue

                arg_value = query_match.group(1)
                if tool.name == "web_search":
                    args = {"query": arg_value}
                elif tool.name == "scrape_webpage":
                    if not arg_value.startswith("http"):
                        continue
                    args = {"url": arg_value}
                elif tool.name == "calculator":
                    args = {"expression": arg_value}
                else:
                    continue

                tc = ToolCall(name=tool.name, arguments=args)
                tr = await self._executor.execute_one(
                    tc, budget=self._budget, usage=self._usage
                )
                return tc, tr

        return None, None

    async def _generate_final(self, messages: list[Message], query: str) -> str:
        """Generate the final answer from a terminal node's history."""
        path = "\n".join(
            m.content[:300]
            for m in messages
            if m.role == Role.ASSISTANT and m.content
        )
        prompt = _FINAL_PROMPT.format(query=query, path=path)
        response = await self._llm.complete(
            messages=[Message(role=Role.USER, content=prompt)],
            model=self._model,
            temperature=0.1,
            max_tokens=self._settings.max_tokens_per_response,
            budget=self._budget,
            usage_tracker=self._usage,
        )
        return response.content or ""
