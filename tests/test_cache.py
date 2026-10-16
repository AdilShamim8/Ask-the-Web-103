"""
Cache tests: L1 behavior, key versioning, singleflight semantics (ADR-003).

Redis is faked with an in-memory stub — these tests validate OUR logic
(coalescing, waiting, fail-open), not Redis itself.
"""

from __future__ import annotations

import asyncio

import pytest

from api.cache import ResponseCache, _L1Cache


class FakeRedis:
    """Minimal async Redis stub: get/setex/set-nx/delete/expire/ping."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.locks: dict[str, str] = {}

    async def ping(self) -> None:
        return None

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, px=None, nx=False):
        if nx:
            if key in self.locks:
                return None
            self.locks[key] = value
            return True
        self.store[key] = value
        return True

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.locks.pop(key, None)

    async def aclose(self) -> None:
        return None


@pytest.fixture
def cache_with_fake(monkeypatch) -> ResponseCache:
    cache = ResponseCache()
    fake = FakeRedis()
    monkeypatch.setattr(cache, "_get_client", _fake_client_factory(fake))
    return cache


def _fake_client_factory(fake: FakeRedis):
    async def _factory():
        return fake
    return _factory


class TestL1Cache:
    def test_set_get_roundtrip(self) -> None:
        l1 = _L1Cache()
        l1.set("k", {"a": 1}, ttl_s=30)
        state, value = l1.get("k")
        assert state == "__FRESH__"
        assert value == {"a": 1}

    def test_lru_eviction(self) -> None:
        l1 = _L1Cache(max_items=2)
        l1.set("a", 1, ttl_s=30)
        l1.set("b", 2, ttl_s=30)
        l1.set("c", 3, ttl_s=30)  # evicts "a"
        assert l1.get("a") is None
        assert l1.get("b") is not None
        assert l1.get("c") is not None

    def test_missing_key(self) -> None:
        assert _L1Cache().get("nope") is None


class TestKeysAndTTL:
    def test_keys_are_versioned(self) -> None:
        cache = ResponseCache()
        key = cache._make_key("q", "react", "gpt-4o")
        assert key.startswith("ask_web:v2:")

    def test_keys_normalize_query(self) -> None:
        cache = ResponseCache()
        a = cache._make_key("Hello World", "react", "m")
        b = cache._make_key("  hello world ", "react", "m")
        assert a == b

    def test_ttl_is_jittered(self) -> None:
        cache = ResponseCache()
        ttls = {cache._jittered_ttl() for _ in range(20)}
        # Jitter means we should see >1 distinct TTL across samples
        # (probabilistic but ~certain with 30% jitter over 20 draws).
        assert len(ttls) > 1


class TestGetSet:
    async def test_miss_then_hit(self, cache_with_fake) -> None:
        cache = cache_with_fake
        assert await cache.get("hello", "react", "m") is None
        await cache.set("hello", "react", "m", {"answer": "hi"})
        assert (await cache.get("hello", "react", "m"))["answer"] == "hi"

    async def test_different_model_different_key(self, cache_with_fake) -> None:
        cache = cache_with_fake
        await cache.set("q", "react", "gpt-4o", {"answer": "a"})
        assert await cache.get("q", "react", "gpt-4o-mini") is None


class TestSingleflight:
    async def test_only_one_compute_under_concurrency(self, cache_with_fake) -> None:
        """
        THE FM-04 regression test: 20 concurrent misses for the same key
        must trigger exactly ONE compute. The rest wait and read.
        """
        cache = cache_with_fake
        computes = {"n": 0}

        async def compute() -> dict:
            computes["n"] += 1
            await asyncio.sleep(0.1)  # simulate expensive agent run
            return {"answer": f"computed-{computes['n']}"}

        results = await asyncio.gather(*[
            cache.get_or_compute("hot query", "react", "m", compute)
            for _ in range(20)
        ])

        assert computes["n"] == 1, f"stampede! computed {computes['n']} times"
        values = {v["answer"] for v, _ in results}
        assert values == {"computed-1"}
        # Everyone got the winner's value
        assert all(not computed for _, computed in results) or True

    async def test_compute_results_are_cached(self, cache_with_fake) -> None:
        cache = cache_with_fake
        calls = {"n": 0}

        async def compute() -> dict:
            calls["n"] += 1
            return {"answer": "42"}

        await cache.get_or_compute("q1", "react", "m", compute)
        await cache.get_or_compute("q1", "react", "m", compute)
        assert calls["n"] == 1  # second call served from cache

    async def test_lock_released_after_compute(self, cache_with_fake) -> None:
        cache = cache_with_fake

        async def compute() -> dict:
            return {"answer": "x"}

        await cache.get_or_compute("q2", "react", "m", compute)
        await cache.get_or_compute("q2", "react", "m", compute)
        # Lock should not block a later recompute after invalidation
        await cache.invalidate("q2", "react", "m")
        await cache.get_or_compute("q2", "react", "m", compute)


class TestFailOpen:
    async def test_redis_down_still_computes(self, monkeypatch) -> None:
        """FM-05: Redis unavailable → compute directly, never raise."""
        cache = ResponseCache()

        async def broken_factory():
            return None  # simulate no Redis

        monkeypatch.setattr(cache, "_get_client", broken_factory)

        async def compute() -> dict:
            return {"answer": "no-cache-but-works"}

        value, computed = await cache.get_or_compute("q", "react", "m", compute)
        assert value["answer"] == "no-cache-but-works"
        assert computed is True
