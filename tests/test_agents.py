from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import AgentType, build_agent
from agents.react_agent import ReACTAgent
from agents.reflexion_agent import ReflexionAgent
from agents.orchestrator import OrchestratorAgent
from core.exceptions import MaxIterationsExceededError
from core.llm_client import LLMClient
from core.message_types import AgentState, Message, Role, ToolCall, ToolResult
from tools import build_default_registry
from tools.tool_executor import ToolExecutor


def make_mock_llm() -> MagicMock:
    """Factory for a mock LLM client."""
    return MagicMock(spec=LLMClient)


def make_final_answer_message(content: str = "Here is the answer.") -> Message:
    return Message(role=Role.ASSISTANT, content=content)


def make_tool_call_message(tool_name: str = "web_search", args: dict | None = None) -> Message:
    return Message(
        role=Role.ASSISTANT,
        tool_calls=[
            ToolCall(name=tool_name, arguments=args or {"query": "test"})
        ],
    )


# ── ReACT Agent ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestReACTAgent:
    def _make_agent(self, llm: MagicMock) -> ReACTAgent:
        registry = build_default_registry()
        executor = ToolExecutor(registry)
        return ReACTAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
        )

    async def test_direct_answer_no_tools(self) -> None:
        """Agent returns final answer immediately without tool calls."""
        llm = make_mock_llm()
        llm.complete = AsyncMock(
            return_value=make_final_answer_message("Paris is the capital of France.")
        )
        agent = self._make_agent(llm)
        state = await agent.run("What is the capital of France?")

        assert state.final_answer == "Paris is the capital of France."
        assert state.iterations == 1
        assert len(state.tool_calls_made) == 0

    async def test_one_tool_then_answer(self) -> None:
        """Agent calls one tool, then gives a final answer."""
        llm = make_mock_llm()

        search_result = ToolResult(
            tool_call_id="call_abc",
            tool_name="calculator",
            content="42",
        )

        llm.complete = AsyncMock(side_effect=[
            make_tool_call_message("calculator", {"expression": "6*7"}),
            make_final_answer_message("6 times 7 equals 42."),
        ])

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_parallel = AsyncMock(return_value=[search_result])
        executor.execute_sequential = AsyncMock(return_value=[search_result])

        agent = ReACTAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
        )
        state = await agent.run("What is 6 times 7?")

        assert state.final_answer == "6 times 7 equals 42."
        assert state.iterations == 2

    async def test_max_iterations_raises(self) -> None:
        """Agent raises MaxIterationsExceededError when loop never ends."""
        llm = make_mock_llm()
        llm.complete = AsyncMock(
            return_value=make_tool_call_message("calculator", {"expression": "1+1"})
        )

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_sequential = AsyncMock(
            return_value=[
                ToolResult(
                    tool_call_id="x",
                    tool_name="calculator",
                    content="2",
                )
            ]
        )
        executor.execute_parallel = AsyncMock(
            return_value=[
                ToolResult(
                    tool_call_id="x",
                    tool_name="calculator",
                    content="2",
                )
            ]
        )

        agent = ReACTAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=3,
        )

        with pytest.raises(MaxIterationsExceededError):
            await agent.run("Loop forever question")

    async def test_initial_state_has_system_message(self) -> None:
        llm = make_mock_llm()
        llm.complete = AsyncMock(return_value=make_final_answer_message())
        agent = self._make_agent(llm)
        state = agent._build_initial_state("test query")

        assert state.messages[0].role == Role.SYSTEM
        assert state.messages[1].role == Role.USER
        assert state.messages[1].content == "test query"

    async def test_sources_extracted_from_search(self) -> None:
        import json
        llm = make_mock_llm()

        search_tool_result = ToolResult(
            tool_call_id="call_search",
            tool_name="web_search",
            content=json.dumps({
                "results": [
                    {"title": "Example", "url": "https://example.com", "snippet": "Test"}
                ],
                "query": "test",
            }),
        )

        llm.complete = AsyncMock(side_effect=[
            make_tool_call_message("web_search", {"query": "test"}),
            make_final_answer_message("Answer with [Source 1]"),
        ])

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_parallel = AsyncMock(return_value=[search_tool_result])
        executor.execute_sequential = AsyncMock(return_value=[search_tool_result])

        agent = ReACTAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
        )
        state = await agent.run("test question")
        assert len(state.sources) == 1
        assert state.sources[0]["url"] == "https://example.com"


# ── Reflexion Agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestReflexionAgent:
    async def test_accepts_good_answer(self) -> None:
        """If reflection verdict is ACCEPT, returns after first pass."""
        llm = make_mock_llm()

        # ReACT call returns answer
        # Reflection call returns ACCEPT
        llm.complete = AsyncMock(side_effect=[
            make_final_answer_message("Great answer here."),  # ReACT
            Message(                                           # Reflection
                role=Role.ASSISTANT,
                content="VERDICT: ACCEPT\nREASON: Answer is complete.",
            ),
        ])

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_parallel = AsyncMock(return_value=[])
        executor.execute_sequential = AsyncMock(return_value=[])

        agent = ReflexionAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
            max_reflections=2,
        )
        state = await agent.run("test query")
        assert state.final_answer == "Great answer here."

    async def test_revises_on_critique(self) -> None:
        """If reflection says REVISE, agent runs again with critique."""
        llm = make_mock_llm()

        llm.complete = AsyncMock(side_effect=[
            make_final_answer_message("Initial answer."),     # ReACT pass 1
            Message(                                           # Reflection → REVISE
                role=Role.ASSISTANT,
                content=(
                    "VERDICT: REVISE\n"
                    "CRITIQUE: Missing key sources.\n"
                    "SUGGESTION: Add citations."
                ),
            ),
            make_final_answer_message("Improved answer."),    # ReACT pass 2
            Message(                                           # Reflection → ACCEPT
                role=Role.ASSISTANT,
                content="VERDICT: ACCEPT\nREASON: Now complete.",
            ),
        ])

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_parallel = AsyncMock(return_value=[])
        executor.execute_sequential = AsyncMock(return_value=[])

        agent = ReflexionAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
            max_reflections=2,
        )
        state = await agent.run("test query")
        assert state.final_answer == "Improved answer."


# ── Orchestrator ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestOrchestratorAgent:
    async def test_decompose_and_synthesize(self) -> None:
        """Orchestrator decomposes, runs workers, synthesizes."""
        import json as _json

        llm = make_mock_llm()

        decompose_msg = Message(
            role=Role.ASSISTANT,
            content=_json.dumps([
                "Sub-question 1",
                "Sub-question 2",
            ]),
        )
        worker_answer = make_final_answer_message("Worker answer.")
        synthesis_answer = make_final_answer_message("Synthesized final answer.")

        # Calls: decompose, worker1 react, worker2 react, synthesize
        llm.complete = AsyncMock(side_effect=[
            decompose_msg,
            worker_answer,
            worker_answer,
            synthesis_answer,
        ])

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_parallel = AsyncMock(return_value=[])
        executor.execute_sequential = AsyncMock(return_value=[])

        agent = OrchestratorAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
            max_workers=2,
        )
        state = await agent.run("Complex multi-part question")

        assert state.final_answer == "Synthesized final answer."
        assert "sub_questions" in state.metadata
        assert len(state.metadata["sub_questions"]) == 2

    async def test_fallback_on_bad_decompose_json(self) -> None:
        """Orchestrator falls back to single question on JSON parse failure."""
        llm = make_mock_llm()

        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content="NOT VALID JSON AT ALL"),
            make_final_answer_message("Fallback answer."),
            make_final_answer_message("Synthesized."),
        ])

        registry = build_default_registry()
        executor = MagicMock(spec=ToolExecutor)
        executor.execute_parallel = AsyncMock(return_value=[])
        executor.execute_sequential = AsyncMock(return_value=[])

        agent = OrchestratorAgent(
            llm_client=llm,
            registry=registry,
            executor=executor,
            max_iterations=5,
        )
        state = await agent.run("Any question")
        # Should not crash — uses original query as fallback
        assert state.final_answer is not None