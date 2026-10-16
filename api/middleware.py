from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from configs.settings import get_settings
from core.exceptions import (
    AgentBaseError,
    ContextWindowExceededError,
    MaxIterationsExceededError,
    SearchError,
    ToolExecutionError,
)

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        structlog.contextvars.unbind_contextvars("request_id")
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=round(elapsed * 1000, 1),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter (per IP).
    In production replace with Redis-backed sliding window.
    """

    def __init__(self, app: Any, requests: int = 100, window: int = 60) -> None:
        super().__init__(app)
        self._requests = requests
        self._window = window
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        hits = self._buckets.get(client_ip, [])
        hits = [t for t in hits if now - t < self._window]

        if len(hits) >= self._requests:
            logger.warning("rate_limit.exceeded", ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Max {self._requests} requests per {self._window}s",
                },
            )

        hits.append(now)
        self._buckets[client_ip] = hits
        return await call_next(request)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return structured JSON errors."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except MaxIterationsExceededError as exc:
            logger.warning("agent.max_iterations", error=str(exc))
            return JSONResponse(
                status_code=422,
                content={"error": "Max iterations exceeded", "detail": str(exc)},
            )
        except ContextWindowExceededError as exc:
            logger.error("agent.context_exceeded", error=str(exc))
            return JSONResponse(
                status_code=422,
                content={"error": "Context window exceeded", "detail": str(exc)},
            )
        except SearchError as exc:
            logger.error("search.failed", error=str(exc))
            return JSONResponse(
                status_code=502,
                content={"error": "Search service unavailable", "detail": str(exc)},
            )
        except ToolExecutionError as exc:
            logger.error("tool.failed", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"error": "Tool execution failed", "detail": str(exc)},
            )
        except AgentBaseError as exc:
            logger.error("agent.error", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"error": "Agent error", "detail": str(exc)},
            )
        except Exception as exc:
            logger.exception("unhandled.error", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"},
            )