"""
Unified LLM client — provider abstraction with health-weighted fallback.

Production behavior (ADR-002):
* Ordered provider preference list, not a single choice: on failure the
  next provider is tried, so a vendor incident degrades us only when BOTH
  are unhealthy (FMEA FM-01).
* Every call runs: budget pre-check → circuit breaker → bounded jittered
  retry → provider call. Retries live INSIDE the breaker so an open
  breaker short-circuits instantly (no retry amplification, FM-03).
* Real token usage is extracted from responses and fed to the request's
  ``UsageTracker``; costs are estimated and exported (FM-07 visibility).
* Two model tiers: ``default_model`` for synthesis, ``fast_model`` for
  routing/classification/cheap sub-calls (capacity doc §3: this split is
  worth ~$84M/yr at target scale).
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import SecretStr

from configs.settings import LLMProvider, get_settings
from core.budgets import BudgetManager
from core.exceptions import LLMError, ProviderUnavailableError
from core.message_types import Message, Role, ToolCall, UsageInfo
from core.resilience import (
    BreakerRegistry,
    retry_with_jitter,
)
from core.usage_tracker import UsageTracker

logger = structlog.get_logger(__name__)

# Exceptions worth retrying at the HTTP/provider transport layer
_TRANSIENT = (TimeoutError, ConnectionError)


class LLMClient:
    """Unified async LLM client supporting OpenAI and Anthropic with fallback."""

    def __init__(self, *, usage_tracker: UsageTracker | None = None) -> None:
        settings = get_settings()
        self._settings = settings
        self._usage: UsageTracker | None = usage_tracker
        self._breakers = BreakerRegistry()

        self._openai = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.llm_timeout,
            max_retries=0,  # WE own retry policy (bounded + jittered + breaker-wrapped)
        )
        self._anthropic = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            timeout=settings.llm_timeout,
            max_retries=0,
        )

        # Ordered preference per provider enum; configured, not hardcoded.
        self._provider_order: list[LLMProvider] = settings.llm_provider_order

    # ── Provider selection ───────────────────────────────────────────────

    def _candidates(self, provider: LLMProvider | None) -> list[LLMProvider]:
        """Provider fallback order for this call."""
        if provider is not None:
            return [provider]
        return self._provider_order

    def _provider_client(self, provider: LLMProvider) -> tuple[Any, str]:
        """Return (client, api_key) or raise if the provider has no key."""
        if provider == LLMProvider.OPENAI:
            return self._openai, self._settings.openai_api_key
        return self._anthropic, self._settings.anthropic_api_key

    @staticmethod
    def _has_key(secret: SecretStr) -> bool:
        return bool(secret.get_secret_value())

    # ── Public API ───────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        provider: LLMProvider | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        fast: bool = False,
        budget: BudgetManager | None = None,
        usage_tracker: UsageTracker | None = None,
    ) -> Message:
        """
        Send messages to the LLM and return the assistant Message.

        ``fast=True`` routes to the cheap model tier (routing, tool
        selection, classification — anywhere the answer is not user-facing).
        ``budget`` is checked BEFORE the call; actual usage is recorded
        AFTER, so budgets converge on real consumption.
        """
        settings = self._settings
        chosen_model = model or (settings.fast_model if fast else settings.default_model)
        max_tokens = max_tokens or settings.max_tokens_per_response
        tracker = usage_tracker or self._usage

        # Budget pre-check: estimate input tokens, reserve the output cap.
        if budget is not None:
            from core.token_counter import TokenCounter

            est_in = TokenCounter.count_messages(messages, chosen_model)
            budget.consume_tokens(input_tokens=est_in, output_tokens=max_tokens)
            budget.check_deadline()

        log = logger.bind(model=chosen_model)
        last_error: Exception | None = None

        for candidate in self._candidates(provider):
            client, key = self._provider_client(candidate)
            if not self._has_key(key):
                logger.debug("llm.skip_no_key", provider=candidate.value)
                continue

            try:
                breaker = self._breakers.get_or_create(f"llm:{candidate.value}")

                async def _call() -> Message:
                    if candidate == LLMProvider.OPENAI:
                        return await self._openai_complete(
                            client, messages, tools, chosen_model,
                            temperature, max_tokens, tracker,
                        )
                    return await self._anthropic_complete(
                        client, messages, tools, chosen_model,
                        temperature, max_tokens, tracker,
                    )

                message = await breaker.call(
                    lambda: retry_with_jitter(
                        _call, attempts=3, base_delay_s=0.5, max_delay_s=5.0,
                        retry_on=_TRANSIENT,
                    )
                )
                from core.observability import LLM_PROVIDER_UP

                LLM_PROVIDER_UP.labels(provider=candidate.value).set(1)
                return message

            except ProviderUnavailableError as exc:
                # Breaker open for this provider — try the next one.
                logger.warning("llm.breaker_open", provider=candidate.value)
                last_error = exc
                continue
            except Exception as exc:
                from core.observability import LLM_PROVIDER_UP

                LLM_PROVIDER_UP.labels(provider=candidate.value).set(0)
                logger.warning(
                    "llm.provider_failed",
                    provider=candidate.value,
                    error=str(exc)[:200],
                )
                last_error = exc
                continue

        raise LLMError(
            f"All LLM providers failed: {last_error}",
            provider="fallback-chain",
            model=chosen_model,
        )

    # ── OpenAI implementation ────────────────────────────────────────────

    async def _openai_complete(
        self,
        client: AsyncOpenAI,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        model: str,
        temperature: float,
        max_tokens: int,
        tracker: UsageTracker | None,
    ) -> Message:
        from core.observability import LLM_CALLS, LLM_LATENCY

        import time as _time

        start = _time.perf_counter()
        serialized = []
        for m in messages:
            if m.role == Role.TOOL and m.tool_results:
                for tr in m.tool_results:
                    serialized.append({
                        "role": "tool",
                        "tool_call_id": tr.tool_call_id,
                        "content": tr.content,
                    })
            else:
                serialized.append(m.to_openai_dict())

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": serialized,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:
            LLM_CALLS.labels(provider="openai", model=model, outcome="error").inc()
            raise

        LLM_LATENCY.labels(provider="openai").observe(_time.perf_counter() - start)
        LLM_CALLS.labels(provider="openai", model=model, outcome="ok").inc()

        usage = UsageInfo.from_openai(response.usage)
        if tracker is not None:
            tracker.record_llm_call("openai", model, usage.input_tokens, usage.output_tokens)

        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] | None = None
        if msg.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in msg.tool_calls
            ]

        return Message(
            role=Role.ASSISTANT,
            content=msg.content,
            tool_calls=tool_calls,
            metadata={
                "finish_reason": choice.finish_reason,
                "provider": "openai",
                "usage": usage.model_dump(),
            },
        )

    # ── Anthropic implementation ─────────────────────────────────────────

    async def _anthropic_complete(
        self,
        client: AsyncAnthropic,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        model: str,
        temperature: float,
        max_tokens: int,
        tracker: UsageTracker | None,
    ) -> Message:
        from core.observability import LLM_CALLS, LLM_LATENCY

        import time as _time

        start = _time.perf_counter()
        system_content = ""
        chat_messages = []
        for m in messages:
            if m.role == Role.SYSTEM:
                system_content += (m.content or "") + "\n"
            else:
                chat_messages.append(m.to_anthropic_dict())

        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {}),
                }
                for t in tools
            ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
        }
        if system_content:
            kwargs["system"] = system_content.strip()
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            response = await client.messages.create(**kwargs)
        except TypeError:
            # SDK compatibility (found 2026-10-16): newer anthropic SDKs
            # reject optional sampling params on some models. Sampling is
            # a nicety, not a requirement — retry once without it.
            kwargs.pop("temperature", None)
            response = await client.messages.create(**kwargs)
        except Exception:
            LLM_CALLS.labels(provider="anthropic", model=model, outcome="error").inc()
            raise

        LLM_LATENCY.labels(provider="anthropic").observe(_time.perf_counter() - start)
        LLM_CALLS.labels(provider="anthropic", model=model, outcome="ok").inc()

        usage = UsageInfo.from_anthropic(response.usage)
        if tracker is not None:
            tracker.record_llm_call(
                "anthropic", model, usage.input_tokens, usage.output_tokens
            )

        text_content = ""
        tool_calls: list[ToolCall] | None = None
        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        return Message(
            role=Role.ASSISTANT,
            content=text_content or None,
            tool_calls=tool_calls,
            metadata={
                "stop_reason": response.stop_reason,
                "provider": "anthropic",
                "usage": usage.model_dump(),
            },
        )

    # ── Streaming ────────────────────────────────────────────────────────

    async def stream_complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream text tokens for final answer delivery (OpenAI transport)."""
        model = model or self._settings.default_model
        max_tokens = max_tokens or self._settings.max_tokens_per_response

        serialized = [
            m.to_openai_dict()
            for m in messages
            if m.role != Role.TOOL or m.tool_results
        ]

        async with self._openai.chat.completions.stream(
            model=model,
            messages=serialized,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ── Health / introspection ───────────────────────────────────────────

    def breaker_stats(self) -> list[dict[str, Any]]:
        """Expose breaker health (used by /readyz and dashboards)."""
        return self._breakers.all_stats()
