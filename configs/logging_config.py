"""
Logging configuration — structured logs with secret redaction.

Production rules:
* JSON logs in staging/production (machine-parseable, ship-anywhere);
  pretty Rich console in development.
* A redaction processor scrubs known secret shapes (``sk-…``, ``tvly-…``,
  bearer tokens) from every rendered event — defense in depth for FMEA
  FM-16, in case a payload containing a key ever reaches a log call.
* Noisy HTTP clients are silenced to WARNING — httpx logs every request
  otherwise, which at production QPS is both cost and noise.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

from configs.settings import get_settings

# Patterns that must never appear in logs. Ordered by specificity.
_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"tvly-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key[\"'\s:=]+)[A-Za-z0-9_\-]{16,}"),
]
_REDACTED = "[REDACTED]"


def redact_secrets(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    """structlog processor: scrub secret-looking values from all fields."""

    def _clean(value):
        if isinstance(value, str):
            for pattern in _SECRET_PATTERNS:
                value = pattern.sub(_REDACTED, value)
            return value
        if isinstance(value, dict):
            return {k: _clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_clean(v) for v in value]
        return value

    return {k: _clean(v) for k, v in event_dict.items()}


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level)
    dev = settings.app_env == "development"

    if dev:
        console = Console(stderr=True)
        logging.basicConfig(
            level=level,
            format="%(message)s",
            handlers=[
                RichHandler(
                    console=console,
                    rich_tracebacks=True,
                    tracebacks_show_locals=True,
                )
            ],
        )
    else:
        # Production: plain stderr handler; structlog renders JSON.
        logging.basicConfig(
            level=level,
            format="%(message)s",
            handlers=[logging.StreamHandler(sys.stderr)],
            force=True,
        )

    # Silence noisy libraries (volume control at production QPS)
    for noisy in ("httpx", "httpcore", "playwright", "openai", "anthropic",
                  "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # NOTE (fixed 2026-10-16): annotated as structlog.typing.Processor —
    # the un-annotated heterogeneous literal inferred list[object], which
    # structlog.configure then rejected.
    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        redact_secrets,
    ]

    # NOTE: structlog.stdlib.add_logger_name is deliberately ABSENT —
    # it requires a stdlib Logger (has .name) and raises AttributeError
    # with our PrintLoggerFactory. Discovered by the test suite
    # (tests/configure structlog globally via lifespan startup);
    # before this fix the app crashed on its first log call after boot.

    structlog.configure(
        processors=[
            *processors,
            structlog.dev.ConsoleRenderer()
            if dev
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
