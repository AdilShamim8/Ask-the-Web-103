"""
HTTP middleware — rate limiting, security headers, logging, errors.

Production changes vs 1.0:
* Rate limiting is Redis-backed (sliding window via ZSET) — limits are
  GLOBAL across pods. The old in-memory limiter meant N pods = N× the
  configured limit, and its per-IP dict grew unboundedly (memory leak).
  Fails open to a bounded in-process window when Redis is down (FM-05).
* Security headers on every response (X-Content-Type-Options,
  X-Frame-Options, Referrer-Policy, HSTS in production).
* Error mapping uses the typed exception model (error codes, severity,
  retryable) — clients get machine-readable failures.
* 429 responses include Retry-After (backoff contract, FM-03).
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from configs.settings import get_settings
from core.exceptions import (
    AgentBaseError,
    BudgetExceededError,
    ContextWindowExceededError,
    MaxIterationsExceededError,
    RateLimitError,
    SearchError,
    ToolExecutionError,
)
from core.observability import HTTP_REQUESTS, RATE_LIMITED

logger = structlog.get_logger(__name__)

_RETRY_AFTER_S = 30


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("request_id")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing + RED metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        route = request.url.path
        HTTP_REQUESTS.labels(
            route=route, method=request.method, status=str(response.status_code)
        ).inc()

        logger.info(
            "http.request",
            method=request.method,
            path=route,
            status_code=response.status_code,
            elapsed_ms=round(elapsed * 1000, 1),
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Standard hardening headers on every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Cache-Control", "no-store"
        )  # answers are per-request, never CDN-cached at browser level
        if get_settings().is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis sliding-window rate limiter (global across pods), with a
    bounded in-process fallback when Redis is unavailable.

    Exempt paths: /healthz, /readyz, /metrics (monitoring must never be
    rate limited — that's how you lose observability during an incident).
    """

    def __init__(self, app, requests: int = 100, window: int = 60) -> None:
        super().__init__(app)
        self._requests = requests
        self._window = window
        self._redis: Any = None
        self._redis_checked = False
        # Fallback state: bounded deques per IP (max 50k IPs, then reset)
        self._local: defaultdict[str, deque] = defaultdict(deque)

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        if self._redis_checked:
            return None
        try:
            import redis.asyncio as aioredis

            client = await aioredis.from_url(
                get_settings().redis_url, decode_responses=True,
            )
            await client.ping()
            self._redis = client
        except Exception:
            self._redis = None
        finally:
            self._redis_checked = True
        return self._redis

    async def _check_redis(self, client_ip: str) -> bool:
        """True = allowed. ZSET sliding window."""
        redis = await self._get_redis()
        if redis is None:
            return self._check_local(client_ip)
        try:
            now_ms = time.time() * 1000
            key = f"rl:{client_ip}"
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, now_ms - self._window * 1000)
            pipe.zcard(key)
            _, count = await pipe.execute()
            if count >= self._requests:
                return False
            pipe = redis.pipeline()
            pipe.zadd(key, {str(now_ms): now_ms})
            pipe.expire(key, self._window + 1)
            await pipe.execute()
            return True
        except Exception as exc:
            logger.warning("ratelimit.redis_error_fallback_local",
                           error=str(exc)[:120])
            return self._check_local(client_ip)

    def _check_local(self, client_ip: str) -> bool:
        """Bounded in-process fallback (single-pod correctness only)."""
        now = time.time()
        if len(self._local) > 50_000:
            self._local.clear()  # hard reset — better than OOM
        hits = self._local[client_ip]
        while hits and now - hits[0] > self._window:
            hits.popleft()
        if len(hits) >= self._requests:
            return False
        hits.append(now)
        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/healthz", "/readyz", "/metrics"):
            return await call_next(request)

        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )

        allowed = await self._check_redis(client_ip)
        if not allowed:
            RATE_LIMITED.labels(scope="global").inc()
            logger.warning("rate_limit.exceeded", ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "detail": (
                        f"Max {self._requests} requests per {self._window}s"
                    ),
                    "retryable": True,
                },
                headers={"Retry-After": str(_RETRY_AFTER_S)},
            )

        return await call_next(request)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Typed exception → structured HTTP error mapping."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        try:
            return await call_next(request)
        except BudgetExceededError as exc:
            return self._json(exc, 422, request_id, warn=True)
        except MaxIterationsExceededError as exc:
            return self._json(exc, 422, request_id, warn=True)
        except ContextWindowExceededError as exc:
            return self._json(exc, 422, request_id, warn=True)
        except RateLimitError as exc:
            return self._json(exc, 429, request_id,
                              headers={"Retry-After": str(_RETRY_AFTER_S)})
        except SearchError as exc:
            return self._json(exc, 502, request_id, warn=True)
        except ToolExecutionError as exc:
            return self._json(exc, 502, request_id, warn=True)
        except AgentBaseError as exc:
            return self._json(exc, exc.http_status, request_id)
        except Exception as exc:
            logger.exception("unhandled.error", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "detail": None,
                    "request_id": request_id,
                },
            )

    @staticmethod
    def _json(
        exc: AgentBaseError,
        status: int,
        request_id: str,
        *,
        warn: bool = False,
        headers: dict | None = None,
    ) -> JSONResponse:
        payload = exc.to_dict()
        payload["request_id"] = request_id
        if warn:
            logger.warning("http.handled_error", **payload)
        else:
            logger.error("http.handled_error", **payload)
        return JSONResponse(status_code=status, content=payload, headers=headers)
