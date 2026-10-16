from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.llm_client import LLMClient
from core.message_types import Message, Role
from evaluation.metrics import TextMetrics
from workflows.parallelization import AnswerVerifier, ParallelVoting
from workflows.prompt_chaining import ChainStep, PromptChain
from workflows.reflection import ReflectionWorkflow
from workflows.routing import QueryClassifier


# ── Prompt Chaining ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestPromptChain:
    def _make_llm(self, responses: list[str]) -> MagicMock:
        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content=r)
            for r in responses
        ])
        return llm

    async def test_single_step(self) -> None:
        llm = self._make_llm(["The answer is 42."])
        chain = PromptChain(llm_client=llm)
        chain.add_step(ChainStep(
            name="step1",
            prompt_template="Question: {query}",
            output_key="result",
        ))
        ctx = await chain.run({"query": "What is the answer?"})
        assert ctx["result"] == "The answer is 42."

    async def test_multi_step_context_passing(self) -> None:
        llm = self._make_llm(["Step1 output", "Step2 used step1"])
        chain = PromptChain(llm_client=llm)
        chain.add_step(ChainStep(
            name="step1",
            prompt_template="Input: {query}",
            output_key="step1_out",
        ))
        chain.add_step(ChainStep(
            name="step2",
            prompt_template="Step1 was: {step1_out}, query: {query}",
            output_key="final",
        ))
        ctx = await chain.run({"query": "hello"})
        assert ctx["step1_out"] == "Step1 output"
        assert ctx["final"] == "Step2 used step1"

    async def test_transform_applied(self) -> None:
        llm = self._make_llm(["hello world"])
        chain = PromptChain(llm_client=llm)
        chain.add_step(ChainStep(
            name="upper",
            prompt_template="{input}",
            output_key="result",
            transform=str.upper,
        ))
        ctx = await chain.run({"input": "test"})
        assert ctx["result"] == "HELLO WORLD"

    async def test_missing_key_raises(self) -> None:
        llm = self._make_llm(["output"])
        chain = PromptChain(llm_client=llm)
        chain.add_step(ChainStep(
            name="bad",
            prompt_template="Value: {missing_key}",
            output_key="result",
        ))
        with pytest.raises(ValueError, match="missing_key"):
            await chain.run({"query": "hello"})

    async def test_fluent_interface(self) -> None:
        llm = self._make_llm(["a", "b", "c"])
        chain = (
            PromptChain(llm_client=llm)
            .add_step(ChainStep("s1", "{q}", "o1"))
            .add_step(ChainStep("s2", "{o1}", "o2"))
            .add_step(ChainStep("s3", "{o2}", "o3"))
        )
        ctx = await chain.run({"q": "test"})
        assert "o3" in ctx


# ── Query Classifier ──────────────────────────────────────────────────────────

class TestQueryClassifier:
    def test_conversational_hello(self) -> None:
        result = QueryClassifier.quick_classify("hello there")
        assert result == "conversational"

    def test_calculation_query(self) -> None:
        result = QueryClassifier.quick_classify("calculate 15% of 200")
        assert result == "calculation"

    def test_returns_none_for_research(self) -> None:
        result = QueryClassifier.quick_classify(
            "What are the latest breakthroughs in quantum computing in 2024?"
        )
        assert result is None

    def test_current_events_not_calculation(self) -> None:
        result = QueryClassifier.quick_classify(
            "What is the current GDP of the United States?"
        )
        # "current" is present but so is "what is" + news-like content
        # Should return None and go to LLM routing
        assert result is None


# ── Parallel Voting ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestParallelVoting:
    async def test_majority_winner(self) -> None:
        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content="Paris"),
            Message(role=Role.ASSISTANT, content="Paris"),
            Message(role=Role.ASSISTANT, content="London"),
        ])

        voter = ParallelVoting(llm_client=llm, num_votes=3)
        majority, counts = await voter.vote(
            messages=[Message(role=Role.USER, content="Capital of France?")]
        )
        assert majority == "Paris"
        assert counts["Paris"] == 2
        assert counts["London"] == 1

    async def test_extract_answer_applied(self) -> None:
        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content="  YES  "),
            Message(role=Role.ASSISTANT, content="YES"),
            Message(role=Role.ASSISTANT, content="NO"),
        ])

        voter = ParallelVoting(llm_client=llm, num_votes=3)
        majority, _ = await voter.vote(
            messages=[Message(role=Role.USER, content="Is it true?")],
            extract_answer=lambda x: x.strip().upper(),
        )
        assert majority == "YES"


# ── Answer Verifier ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAnswerVerifier:
    async def test_true_verdict(self) -> None:
        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content="TRUE"),
            Message(role=Role.ASSISTANT, content="TRUE"),
            Message(role=Role.ASSISTANT, content="TRUE"),
        ])

        verifier = AnswerVerifier(llm_client=llm, num_votes=3)
        result = await verifier.verify(
            claim="Water boils at 100°C at sea level.",
            context="Water's boiling point is 100 degrees Celsius at 1 atm pressure.",
        )
        assert result["verdict"] == "TRUE"
        assert result["confidence"] == 1.0

    async def test_uncertain_verdict(self) -> None:
        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content="UNCERTAIN"),
            Message(role=Role.ASSISTANT, content="TRUE"),
            Message(role=Role.ASSISTANT, content="UNCERTAIN"),
        ])

        verifier = AnswerVerifier(llm_client=llm, num_votes=3)
        result = await verifier.verify(claim="Some claim.", context="Limited context.")
        assert result["verdict"] == "UNCERTAIN"


# ── Reflection Workflow ───────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestReflectionWorkflow:
    async def test_no_issues_skips_revision(self) -> None:
        llm = MagicMock(spec=LLMClient)
        llm.complete = AsyncMock(return_value=Message(
            role=Role.ASSISTANT,
            content="No issues found.",
        ))
        llm._settings = MagicMock()
        llm._settings.max_tokens_per_response = 1024

        workflow = ReflectionWorkflow(llm_client=llm, rounds=2)
        result = await workflow.run("What is AI?", "AI is artificial intelligence.")

        assert result["final_answer"] == "AI is artificial intelligence."
        # Only the critique call should have been made (1 call, then early exit)
        assert llm.complete.call_count == 1

    async def test_revision_applied(self) -> None:
        llm = MagicMock(spec=LLMClient)
        llm._settings = MagicMock()
        llm._settings.max_tokens_per_response = 1024

        llm.complete = AsyncMock(side_effect=[
            Message(role=Role.ASSISTANT, content="• Missing examples"),
            Message(role=Role.ASSISTANT, content="Improved answer with examples."),
        ])

        workflow = ReflectionWorkflow(llm_client=llm, rounds=1)
        result = await workflow.run("Explain ML", "ML is machine learning.")

        assert result["final_answer"] == "Improved answer with examples."
        assert len(result["rounds"]) == 1


# ── Text Metrics ──────────────────────────────────────────────────────────────

class TestTextMetrics:
    def test_citation_coverage_full(self) -> None:
        sources = [{"url": "https://example.com", "title": "Example"}]
        answer = "According to example.com, this is true."
        score = TextMetrics.citation_coverage(answer, sources)
        assert score == 1.0

    def test_citation_coverage_none(self) -> None:
        sources = [{"url": "https://obscure-site.xyz/page", "title": "X"}]
        answer = "Nothing cited here at all."
        score = TextMetrics.citation_coverage(answer, sources)
        assert score == 0.0

    def test_citation_coverage_empty_sources(self) -> None:
        score = TextMetrics.citation_coverage("any answer", [])
        assert score == 1.0

    def test_length_score_too_short(self) -> None:
        score = TextMetrics.answer_length_score("short", min_words=50)
        assert score < 1.0

    def test_length_score_ideal(self) -> None:
        text = " ".join(["word"] * 200)
        score = TextMetrics.answer_length_score(text)
        assert score == 1.0

    def test_has_structure_with_headers(self) -> None:
        answer = "## Introduction\nSome text.\n- Bullet 1\n- Bullet 2"
        score = TextMetrics.has_structure(answer)
        assert score >= 0.7

    def test_has_structure_plain_text(self) -> None:
        answer = "This is just a plain answer with no markdown."
        score = TextMetrics.has_structure(answer)
        assert score == 0.0

    def test_sources_section_present(self) -> None:
        answer = "Some answer.\n\n## Sources\n- https://example.com"
        assert TextMetrics.sources_section_present(answer) is True

    def test_sources_section_absent(self) -> None:
        answer = "Some answer with no sources section."
        assert TextMetrics.sources_section_present(answer) is False