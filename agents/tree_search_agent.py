from __future__ import annotations

"""
Tree Search Agent (Best-First Search over reasoning paths).

Implements a simplified Monte Carlo Tree Search (MCTS) / Beam Search
over reasoning trajectories.

Concept:
    - Root node = initial query
    - Each node = (messages_so_far, last_thought)
    - Expand = ask LLM to generate K candidate next thoughts/actions
    - Score  = ask LLM to evaluate how promising each branch is (0-1)
    - Select = pick the highest-scoring branch
    - Terminate = when a branch produces a final answer

Useful for:
    - Multi-hop reasoning with ambiguous intermediate steps
    - Mathematical proof search
    - Code debugging with multiple hypotheses
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from agents.base_agent import BaseAgent
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


@dataclass
class TreeNode:
    thought: str
    messages: list[Message]
    score: float = 0.5
    depth: int = 0
    children: list["TreeNode"] = field(default_factory=list)
    is_terminal: bool = False
    final_answer: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)


class TreeSearchAgent(BaseAgent):
    """
    Best-First Tree Search Agent.
    Explores multiple reasoning paths and picks the most promising one.
    """

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
    ) -> None:
        super().__init__(llm_client, registry, executor, model, max_iterations)
        self._branching_factor = branching_factor
        self._max_depth = max_depth
        self._beam_width = beam_width

    async def run(self, query: str, **kwargs: Any) -> AgentState:
        start = time.perf_counter()
        state = self._build_initial_state(query)
        log = logger.bind(agent="TreeSearch", query=query[:60])
        log.info("tree_search.start",
                 branching=self._branching_factor,
                 max_depth=self._max_depth)

        # Initialize root
        root = TreeNode(
            thought="Starting search...",
            messages=list(state.messages),
            score=1.0,
            depth=0,
        )

        # Beam: keep top-K nodes at each level
        beam: list[TreeNode] = [root]
        best_terminal: TreeNode | None = None

        for depth in range(self._max_depth):
            state.iterations += 1
            log.debug("tree_search.depth", depth=depth, beam_size=len(beam))

            # Expand all nodes in current beam
            next_candidates: list[TreeNode] = []

            expand_tasks = [
                self._expand_node(node, query)
                for node in beam
            ]
            expanded_batches = await asyncio.gather(*expand_tasks)

            for node, children in zip(beam, expanded_batches):
                node.children = children
                next_candidates.extend(children)

            if not next_candidates:
                break

            # Score all candidates in parallel
            score_tasks = [
                self._score_node(node, query)
                for node in next_candidates
            ]
            scores = await asyncio.gather(*score_tasks)

            for node, score in zip(next_candidates, scores):
                node.score = score

            # Check for terminal nodes (final answers)
            terminals = [n for n in next_candidates if n.is_terminal]
            if terminals:
                best_terminal = max(terminals, key=lambda n: n.score)
                log.info("tree_search.terminal_found", score=best_terminal.score)
                break

            # Select top beam_width for next iteration
            next_candidates.sort(key=lambda n: n.score, reverse=True)
            beam = next_candidates[: self._beam_width]
            log.debug(
                "tree_search.beam_selected",
                top_scores=[round(n.score, 2) for n in beam],
            )

        # ── Extract final answer ──────────────────────────────────────────
        if best_terminal and best_terminal.final_answer:
            state.final_answer = best_terminal.final_answer
            state.tool_calls_made = best_terminal.tool_calls
            state.tool_results_received = best_terminal.tool_results
        else:
            # No terminal found — synthesize from best beam node
            best = max(beam, key=lambda n: n.score) if beam else root
            state.final_answer = await self._synthesize(best, query)

        self._extract_sources(state)
        self._log_state_summary(state, time.perf_counter() - start)
        return state

    async def _expand_node(
        self, node: TreeNode, query: str
    ) -> list[TreeNode]:
        """Generate branching_factor candidate children for a node."""
        history = "\n".join(
            f"- {m.content[:200]}"
            for m in node.messages
            if m.role == Role.ASSISTANT and m.content
        ) or "No steps yet."

        prompt = _EXPAND_PROMPT.format(
            query=query,
            history=history,
            branching_factor=self._branching_factor,
        )

        response = await self._llm.complete(
            messages=[Message(role=Role.USER, content=prompt)],
            model=self._model,
            temperature=0.8,    # Higher temp for diverse candidates
            max_tokens=512,
        )

        raw = response.content or ""
        candidates = self._parse_candidates(raw)

        children = []
        for thought in candidates:
            # Check if this thought implies a tool call
            tool_call, tool_result = await self._maybe_execute_tool(thought, query)

            child_messages = list(node.messages)
            child_messages.append(Message(role=Role.ASSISTANT, content=thought))

            is_terminal = self._is_final_answer(thought)
            final_answer = ""

            if is_terminal:
                final_answer = await self._generate_final(child_messages, query)

            child = TreeNode(
                thought=thought,
                messages=child_messages,
                depth=node.depth + 1,
                is_terminal=is_terminal,
                final_answer=final_answer,
                tool_calls=node.tool_calls + ([tool_call] if tool_call else []),
                tool_results=node.tool_results + ([tool_result] if tool_result else []),
            )
            children.append(child)

        return children

    def _parse_candidates(self, text: str) -> list[str]:
        """Extract candidate thoughts from the expansion response."""
        candidates = []
        for line in text.splitlines():
            match = __import__("re").match(
                r"CANDIDATE\s+\d+:\s*(.+)", line, __import__("re").IGNORECASE
            )
            if match:
                candidates.append(match.group(1).strip())
        return candidates or [text.strip()]

    async def _score_node(self, node: TreeNode, query: str) -> float:
        """Ask the LLM to score how promising this reasoning path is."""
        path = "\n".join(
            m.content[:200]
            for m in node.messages
            if m.role == Role.ASSISTANT and m.content
        ) or "Empty path"

        prompt = _SCORE_PROMPT.format(
            query=query,
            path=path,
            candidate=node.thought,
        )

        try:
            response = await self._llm.complete(
                messages=[Message(role=Role.USER, content=prompt)],
                model=self._model,
                temperature=0.0,
                max_tokens=10,
            )
            raw = (response.content or "0.5").strip()
            score = float(__import__("re").search(r"\d+\.?\d*", raw).group())
            return min(1.0, max(0.0, score))
        except Exception:
            return 0.5

    def _is_final_answer(self, thought: str) -> bool:
        """Heuristic: detect if the LLM is proposing a final answer."""
        indicators = [
            "final answer", "in conclusion", "therefore,",
            "to summarize", "the answer is", "based on my research",
        ]
        lower = thought.lower()
        return any(ind in lower for ind in indicators)

    async def _maybe_execute_tool(
        self, thought: str, query: str
    ) -> tuple[ToolCall | None, ToolResult | None]:
        """
        Detect if the thought describes a tool use and execute it.
        Simple heuristic: look for tool names in the thought text.
        """
        import re
        for tool in self._registry.all_tools():
            if tool.name in thought.lower():
                # Extract a search query or URL from the thought
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
                tr = await self._executor.execute_one(tc)
                return tc, tr

        return None, None

    async def _generate_final(
        self, messages: list[Message], query: str
    ) -> str:
        """Generate final answer from a terminal node's message history."""
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
        )
        return response.content or ""

    async def _synthesize(self, node: TreeNode, query: str) -> str:
        """Fallback synthesis from the best non-terminal node."""
        return await self._generate_final(node.messages, query)