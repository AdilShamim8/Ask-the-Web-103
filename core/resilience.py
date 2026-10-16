"""
Resilience primitives: circuit breakers, jittered retries, token buckets.

These three tools are the codebase's defense against cascading failure
(FMEA FM-01, FM-02, FM-03). Rules of engagement:

* Retries are **bounded** (hard max attempts) and **jittered** (full jitter
  prevents synchronized retry waves across pods).
* Retries happen **inside** a per-provider circuit breaker. When the breaker
  is open we fail fast — no latency penalty, no retry amplification.
* Token buckets gate local concurrency against external services so a
  provider quota is never exceeded by our own fan-out.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from enum import IntEnum
from typing import Any, TypeVar

import structlog

from core.exceptions import AgentBaseError, ProviderUnavailableError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ── Circuit Breaker ───────────────────────────────────────────────────────────


class BreakerState(IntEnum):
    CLOSED = 0      # healthy: traffic flows
    OPEN = 1        # tripped: fail fast
    HALF_OPEN = 2   # probing: limited traffic to test recovery


class CircuitBreaker:
    """
    Async circuit breaker with failure-rate tripping.

    Trips when ``failure_rate >= failure_rate_threshold`` over the last
    ``window_s`` AND minimum volume ``min_calls_in_window`` was reached.
    After ``recovery_timeout_s`` it goes HALF_OPEN and lets
    ``half_open_max_probes`` concurrent calls through; one failure
    re-opens it, ``success_threshold`` successes close it.
    """

    def __init__(
        self,
        name: str,
        *,
        failure_rate_threshold: float = 0.5,
        min_calls_in_window: int = 10,
        window_s: float = 30.0,
        recovery_timeout_s: float = 60.0,
        half_open_max_probes: int = 3,
        success_threshold: int = 3,
    ) -> None:
        self.name = name
        self._failure_rate_threshold = failure_rate_threshold
        self._min_calls = min_calls_in_window
        self._window_s = window_s
        self._recovery_timeout_s = recovery_timeout_s
        self._half_open_max_probes = half_open_max_probes
        self._success_threshold = success_threshold

        self._state = BreakerState.CLOSED
        self._opened_at: float = 0.0
        self._calls: list[tuple[float, bool]] = []  # (timestamp, success)
        self._half_open_successes = 0
        self._half_open_inflight = 0
        self._lock = asyncio.Lock()

    # ── State machine ────────────────────────────────────────────────────

    @property
    def state(self) -> BreakerState:
        if self._state == BreakerState.OPEN:
            if time.monotonic() - self._opened_at >= self._recovery_timeout_s:
                return BreakerState.HALF_OPEN
        return self._state

    def allow_call(self) -> bool:
        """Non-async fast check; reserve probe slots for HALF_OPEN."""
        state = self.state
        if state == BreakerState.CLOSED:
            return True
        if state == BreakerState.OPEN:
            return False
        # HALF_OPEN: bounded probes
        return self._half_open_inflight < self._half_open_max_probes

    async def _enter_half_open(self) -> None:
        async with self._lock:
            if self._state == BreakerState.OPEN and (
                time.monotonic() - self._opened_at >= self._recovery_timeout_s
            ):
                self._state = BreakerState.HALF_OPEN
                self._half_open_successes = 0
                self._half_open_inflight = 0

    def record_success(self) -> None:
        now = time.monotonic()
        self._prune(now)
        self._calls.append((now, True))

        if self._state == BreakerState.HALF_OPEN:
            self._half_open_successes += 1
            self._half_open_inflight = max(0, self._half_open_inflight - 1)
            if self._half_open_successes >= self._success_threshold:
                self._state = BreakerState.CLOSED
                logger.info("breaker.closed", breaker=self.name)
        elif self._state == BreakerState.OPEN:
            pass  # late success from before the trip; ignore for state

    def record_failure(self) -> None:
        now = time.monotonic()
        self._prune(now)
        self._calls.append((now, False))

        if self._state == BreakerState.HALF_OPEN:
            self._half_open_inflight = max(0, self._half_open_inflight - 1)
            self._trip()
            return

        # CLOSED: evaluate failure rate over window
        if len(self._calls) >= self._min_calls:
            failures = sum(1 for _, ok in self._calls if not ok)
            rate = failures / len(self._calls)
            if rate >= self._failure_rate_threshold:
                self._trip()

    def _trip(self) -> None:
        self._state = BreakerState.OPEN
        self._opened_at = time.monotonic()
        self._half_open_successes = 0
        logger.warning("breaker.opened", breaker=self.name)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window_s
        self._calls = [(t, ok) for t, ok in self._calls if t > cutoff]

    # ── Wrapped call ─────────────────────────────────────────────────────

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """
        Execute ``fn`` under breaker protection.
        Raises ``ProviderUnavailableError`` immediately when OPEN.
        """
        await self._enter_half_open()

        if not self.allow_call():
            logger.debug("breaker.fail_fast", breaker=self.name)
            raise ProviderUnavailableError(
                f"circuit open for '{self.name}'", context={"breaker": self.name}
            )

        if self.state == BreakerState.HALF_OPEN:
            self._half_open_inflight += 1

        try:
            result = await fn()
        except AgentBaseError as exc:
            if exc.retryable:
                self.record_failure()
            else:
                # Non-retryable = our bug or a client error, not provider health
                self.record_success()
            raise
        except Exception:
            self.record_failure()
            raise

        self.record_success()
        return result

    def stats(self) -> dict[str, Any]:
        now = time.monotonic()
        self._prune(now)
        total = len(self._calls)
        failures = sum(1 for _, ok in self._calls if not ok)
        return {
            "name": self.name,
            "state": self.state.name,
            "calls_in_window": total,
            "failures_in_window": failures,
            "failure_rate": round(failures / total, 3) if total else 0.0,
        }


class BreakerRegistry:
    """Named breaker collection — one per provider/remote agent."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(self, name: str, **kwargs: Any) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, **kwargs)
        return self._breakers[name]

    def all_stats(self) -> list[dict[str, Any]]:
        return [b.stats() for b in self._breakers.values()]


# ── Jittered retry ───────────────────────────────────────────────────────────


async def retry_with_jitter(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 5.0,
    retry_on: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError),
) -> T:
    """
    Bounded retry with exponential backoff + full jitter.

    Full jitter (random between 0 and the exponential delay) is the
    recommended strategy against synchronized retry storms (AWS
    Architecture Blog, "Exponential Backoff and Jitter"). Hard cap on
    attempts is non-negotiable: retries are an amplifier during incidents.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except retry_on as exc:
            last_exc = exc
            if attempt == attempts:
                break
            delay = random.uniform(0, min(max_delay_s, base_delay_s * 2 ** (attempt - 1)))
            logger.debug(
                "retry.attempt", attempt=attempt, delay_s=round(delay, 2),
                error=str(exc),
            )
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


# ── Token bucket (local concurrency/quota gate) ───────────────────────────────


class TokenBucket:
    """
    Classic token-bucket rate limiter for local call shaping.

    Use before fanning out to metered external services (search APIs) so
    our own parallelism never trips their quotas. For cross-pod fairness,
    the API layer adds the Redis-backed limiter (api/middleware.py); this
    bucket is the per-process guard.
    """

    def __init__(self, rate_per_s: float, capacity: int) -> None:
        self._rate = rate_per_s
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, *, wait: bool = True) -> bool:
        """
        Take ``tokens`` from the bucket.
        ``wait=True`` blocks until available; ``wait=False`` returns False
        immediately when exhausted (drop/defer path).
        """
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            if not wait:
                return False
            # Sleep a fraction of one token's refill time, then re-check.
            await asyncio.sleep(tokens / self._rate / 2)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
