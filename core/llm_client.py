from __future__ import annotations

import json
from typing import Any, AsyncIterator

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from configs.settings import LLMProvider, get_settings
from core.exceptions import LLMError
from core.message_types import Message, Role, ToolCall

logger = structlog.get_logger(__name__)


class LLMClient:
    """
    Unified async LLM client supporting OpenAI and Anthropic.
    Handles retries, tool call parsing, and token-safe responses.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings

        self._openai = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.llm_timeout,
        )
        self._anthropic = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            timeout=settings.llm_timeout,
        )

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        provider: LLMProvider | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> Message:
        """
        Send messages to the LLM and return the assistant Message.
        Automatically retries on transient errors.
        """
        model = model or self._settings.default_model
        provider = provider or self._settings.default_llm_provider
        max_tokens = max_tokens or self._settings.max_tokens_per_response

        log = logger.bind(model=model, provider=provider.value)
        log.debug("llm_complete.start", num_messages=len(messages))

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type((TimeoutError, ConnectionError)),
                reraise=True,
            ):
                with attempt:
                    if provider == LLMProvider.OPENAI:
                        return await self._openai_complete(
                            messages, tools, model, temperature, max_tokens
                        )
                    else:
                        return await self._anthropic_complete(
                            messages, tools, model, temperature, max_tokens
                        )
        except Exception as exc:
            log.error("llm_complete.failed", error=str(exc))
            raise LLMError(str(exc), provider=provider.value, model=model) from exc

    async def _openai_complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Message:
        serialized = []
        for m in messages:
            if m.role == Role.TOOL and m.tool_results:
                # OpenAI: one message per tool result
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

        response = await self._openai.chat.completions.create(**kwargs)
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
            metadata={"finish_reason": choice.finish_reason},
        )

    async def _anthropic_complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Message:
        system_content = ""
        chat_messages = []

        for m in messages:
            if m.role == Role.SYSTEM:
                system_content += (m.content or "") + "\n"
            else:
                chat_messages.append(m.to_anthropic_dict())

        # Convert OpenAI tool format → Anthropic tool format
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
            "temperature": temperature,
        }
        if system_content:
            kwargs["system"] = system_content.strip()
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = await self._anthropic.messages.create(**kwargs)

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
            metadata={"stop_reason": response.stop_reason},
        )

    async def stream_complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream text tokens for final answer delivery."""
        model = model or self._settings.default_model
        max_tokens = max_tokens or self._settings.max_tokens_per_response

        serialized = [m.to_openai_dict() for m in messages
                      if m.role != Role.TOOL or m.tool_results]

        async with self._openai.chat.completions.stream(
            model=model,
            messages=serialized,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text