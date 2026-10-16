"""
Resilience primitive tests: circuit breaker, jittered retry, token bucket.

These are the regression suites for FMEA FM-01/FM-03 — the mechanisms
that stop cascade amplification. They use a FAKE clock-free design:
breakers use time.monotonic, so we simulate failures fast rather than
time-travel; recovery-timeout paths use short configured values.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from core.exceptions import ProviderUnavailableError
from core.resilience import (
    BreakerRegistry,
    CircuitBreaker,
    TokenBucket,
    retry_with_jitter,
)


class TestCircuitBreaker:
    async def test_closed_allows_traffic(self) -> None:
        breaker = CircuitBreaker("test-ok")

        async def ok():
            return 42

        assert await breaker.call(ok) == 42
        assert breaker.state.name == "CLOSED"

    async def test_opens_after_failure_threshold(self) -> None:
        breaker = CircuitBreaker(
            "test-trip",
            failure_rate_threshold=0.5,
            min_calls_in_window=4,
            window_s=30,
        )

        async def fail():
            raise ConnectionError("boom")

        for _ in range(4):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        assert breaker.state.name == "OPEN"

    async def test_open_fails_fast_without_calling(self) -> None:
        breaker = CircuitBreaker(
            "test-fastfail",
            failure_rate_threshold=0.5,
            min_calls_in_window=2,
            window_s=30,
        )

        calls = {"n": 0}

        async def fail():
            calls["n"] += 1
            raise ConnectionError("boom")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        assert breaker.state.name == "OPEN"

        with pytest.raises(ProviderUnavailableError):
            await breaker.call(fail)

        assert calls["n"] == 2  # fail-fast: no additional call made

    async def test_recovers_after_timeout(self) -> None:
        breaker = CircuitBreaker(
            "test-recover",
            failure_rate_threshold=0.5,
            min_calls_in_window=2,
            window_s=30,
            recovery_timeout_s=0.05,  # tiny for test speed
            success_threshold=1,
        )

        async def fail():
            raise ConnectionError("boom")

        async def ok():
            return "healthy"

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)
        assert breaker.state.name == "OPEN"

        await asyncio.sleep(0.06)  # past recovery timeout
        assert await breaker.call(ok) == "healthy"
        assert breaker.state.name == "CLOSED"

    async def test_non_retryable_errors_do_not_trip(self) -> None:
        """Client errors (our bug, not provider health) must not open
        the breaker — tripping on them would take capacity offline for
        no reason."""
        from core.exceptions import ValidationError

        breaker = CircuitBreaker("test-client-error", min_calls_in_window=2)

        async def client_error():
            raise ValidationError("bad input")

        for _ in range(5):
            with pytest.raises(ValidationError):
                await breaker.call(client_error)

        assert breaker.state.name == "CLOSED"

    def test_stats_shape(self) -> None:
        breaker = CircuitBreaker("stats")
        stats = breaker.stats()
        assert stats["name"] == "stats"
        assert stats["state"] == "CLOSED"
        assert stats["failure_rate"] == 0.0


class TestBreakerRegistry:
    def test_get_or_create_is_idempotent(self) -> None:
        registry = BreakerRegistry()
        a = registry.get_or_create("llm:openai")
        b = registry.get_or_create("llm:openai")
        assert a is b
        assert len(registry.all_stats()) == 1


class TestRetryWithJitter:
    async def test_returns_on_first_success(self) -> None:
        calls = {"n": 0}

        async def ok():
            calls["n"] += 1
            return "fine"

        assert await retry_with_jitter(ok, attempts=3) == "fine"
        assert calls["n"] == 1

    async def test_retries_then_succeeds(self) -> None:
        calls = {"n": 0}

        async def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise TimeoutError("slow")
            return "recovered"

        result = await retry_with_jitter(
            flaky, attempts=5, base_delay_s=0.001, max_delay_s=0.01,
            retry_on=(TimeoutError,),
        )
        assert result == "recovered"
        assert calls["n"] == 3

    async def test_hard_stops_at_attempts(self) -> None:
        """The bound is non-negotiable — retries must never exceed the
        configured attempts (FM-03)."""
        calls = {"n": 0}

        async def always_fails():
            calls["n"] += 1
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await retry_with_jitter(
                always_fails, attempts=3, base_delay_s=0.001,
                retry_on=(ConnectionError,),
            )
        assert calls["n"] == 3

    async def test_does_not_retry_non_matching_errors(self) -> None:
        calls = {"n": 0}

        async def value_error():
            calls["n"] += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await retry_with_jitter(
                value_error, attempts=3, retry_on=(TimeoutError,)
            )
        assert calls["n"] == 1


class TestTokenBucket:
    async def test_allows_burst_up_to_capacity(self) -> None:
        bucket = TokenBucket(rate_per_s=100, capacity=3)
        assert await bucket.acquire(1, wait=False)
        assert await bucket.acquire(1, wait=False)
        assert await bucket.acquire(1, wait=False)
        assert not await bucket.acquire(1, wait=False)  # empty

    async def test_refills_over_time(self) -> None:
        bucket = TokenBucket(rate_per_s=1000, capacity=2)
        assert await bucket.acquire(2, wait=False)
        assert not await bucket.acquire(1, wait=False)
        await asyncio.sleep(0.01)  # ~10 tokens at 1000/s
        assert await bucket.acquire(1, wait=False)

    async def test_wait_blocks_until_available(self) -> None:
        bucket = TokenBucket(rate_per_s=200, capacity=1)
        assert await bucket.acquire(1, wait=False)
        start = time.monotonic()
        assert await bucket.acquire(1, wait=True)  # waits for refill
        assert time.monotonic() - start > 0.001
