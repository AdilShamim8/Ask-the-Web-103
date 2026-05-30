from __future__ import annotations

import logging
import sys

import structlog
from rich.console import Console
from rich.logging import RichHandler

from configs.settings import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level)

    console = Console(stderr=True)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=settings.app_env == "development",
            )
        ],
    )

    # Silence noisy libraries
    for noisy in ("httpx", "httpcore", "playwright"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer()
            if settings.app_env == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )