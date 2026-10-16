"""
Shared test fixtures.

Two global problems this conftest solves:
1. structlog state pollution: API tests trigger the app lifespan, which
   reconfigures structlog globally. We configure a TEST-SAFE rendering
   (no stdlib processors that assume stdlib loggers) once, before any
   test imports run side effects.
2. Provider keys: no test may require OPENAI_API_KEY etc. Everything
   external is faked at the core/ boundary (ADR-001).
"""

from __future__ import annotations

import os

import pytest
import structlog

# Test env: cheap budgets, deterministic, no external calls.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-real")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test-not-real")


def pytest_configure(config):
    """Safe structlog config for the whole session (console, quiet)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING+
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,  # tests may reconfigure
    )


@pytest.fixture(autouse=True)
def _clean_http_client(monkeypatch):
    """Isolate the shared HTTP pool per test — no cross-test state."""
    from tools import http_client

    monkeypatch.setattr(http_client, "_client", None)
    yield
    # nothing to close: pool was rebuilt (or mocked) per test
