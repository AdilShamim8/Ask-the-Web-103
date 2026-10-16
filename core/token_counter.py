"""
Token counting and context management.

Performance notes (FMEA FM-11):
* tiktoken encoding runs on CPU (µs–ms per KB). It stays on the hot path
  only for count_messages/trim; the encoder object is cached per model at
  class level so we pay construction once.
* ``count_tokens`` of very large texts (rare — e.g., full page dumps) is
  CPU-bound; call sites that handle untrusted sizes use the estimator
  instead of the exact counter.
"""

from __future__ import annotations

import json

import tiktoken

from core.message_types import Message, Role

_IMAGE_TOKEN_ESTIMATE = 765

# Fallback ratio: chars per token for cl100k-ish tokenizers on English+code.
_CHARS_PER_TOKEN_ESTIMATE = 4


class TokenCounter:
    """Counts tokens for OpenAI-compatible models; estimates otherwise."""

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
    def estimate_tokens(cls, text: str) -> int:
        """Cheap character-based estimate — for budget pre-checks on
        untrusted/large payloads where exact counting costs more than the
        decision it informs."""
        return max(1, len(text) // _CHARS_PER_TOKEN_ESTIMATE)

    @classmethod
    def count_messages(cls, messages: list[Message], model: str = "gpt-4o") -> int:
        """Token count across a message list (OpenAI framing overhead)."""
        enc = cls._get_encoder(model)
        tokens_per_message = 3
        total = 0

        for msg in messages:
            total += tokens_per_message
            total += len(enc.encode(msg.content or ""))

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += len(enc.encode(tc.name))
                    total += len(enc.encode(json.dumps(tc.arguments)))

            if msg.tool_results:
                for tr in msg.tool_results:
                    total += len(enc.encode(tr.content))

        return total + 3  # reply priming

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
        Trim oldest non-system messages until history fits.
        Preserves system messages and the latest user message.

        Correctness note: this preserves ORDER of the remaining messages
        (system first, then chronological) — trimming never reorders.
        """
        if cls.fits_in_context(messages, model, context_limit, reserved_for_response):
            return messages

        system_msgs = [m for m in messages if m.role == Role.SYSTEM]
        non_system = [m for m in messages if m.role != Role.SYSTEM]
        latest_user = next(
            (m for m in reversed(non_system) if m.role == Role.USER), None
        )

        while non_system and not cls.fits_in_context(
            system_msgs + non_system, model, context_limit, reserved_for_response
        ):
            # Never drop the latest user message — agents spiral without it.
            if len(non_system) == 1 and non_system[0] is latest_user:
                break
            non_system.pop(0)

        return system_msgs + non_system
