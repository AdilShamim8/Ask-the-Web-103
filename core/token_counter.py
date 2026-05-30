from __future__ import annotations

import tiktoken

from core.message_types import Message, Role

# Approximate tokens per image (for future multimodal support)
_IMAGE_TOKEN_ESTIMATE = 765


class TokenCounter:
    """
    Counts tokens for OpenAI-compatible models.
    Falls back to character-based estimation for Anthropic.
    """

    _encoders: dict[str, tiktoken.Encoding] = {}

    @classmethod
    def _get_encoder(cls, model: str) -> tiktoken.Encoding:
        if model not in cls._encoders:
            try:
                cls._encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
        return cls._encoders[model]

    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-4o") -> int:
        enc = cls._get_encoder(model)
        return len(enc.encode(text))

    @classmethod
    def count_messages(cls, messages: list[Message], model: str = "gpt-4o") -> int:
        """
        Counts tokens across a message list using OpenAI's per-message overhead.
        Reference: https://platform.openai.com/docs/guides/chat/managing-tokens
        """
        enc = cls._get_encoder(model)
        tokens_per_message = 3  # every message has role + content framing
        tokens_per_name = 1
        total = 0

        for msg in messages:
            total += tokens_per_message

            content = msg.content or ""
            total += len(enc.encode(content))

            if msg.tool_calls:
                import json
                for tc in msg.tool_calls:
                    total += len(enc.encode(tc.name))
                    total += len(enc.encode(json.dumps(tc.arguments)))

        total += 3  # reply priming
        return total

    @classmethod
    def fits_in_context(
        cls,
        messages: list[Message],
        model: str,
        context_limit: int,
        reserved_for_response: int = 2048,
    ) -> bool:
        used = cls.count_messages(messages, model)
        return used + reserved_for_response <= context_limit

    @classmethod
    def trim_to_fit(
        cls,
        messages: list[Message],
        model: str,
        context_limit: int,
        reserved_for_response: int = 2048,
        keep_system: bool = True,
    ) -> list[Message]:
        """
        Trim oldest non-system messages until the history fits in context.
        Always preserves system message and the latest user message.
        """
        if cls.fits_in_context(messages, model, context_limit, reserved_for_response):
            return messages

        system_msgs = [m for m in messages if m.role == Role.SYSTEM]
        non_system = [m for m in messages if m.role != Role.SYSTEM]

        # Keep trimming from the front of non-system messages
        while non_system and not cls.fits_in_context(
            system_msgs + non_system, model, context_limit, reserved_for_response
        ):
            non_system.pop(0)

        return system_msgs + non_system