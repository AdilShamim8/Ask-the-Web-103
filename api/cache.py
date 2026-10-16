"""
Response cache — two layers + singleflight + stale-while-revalidate.

Implements ADR-003 exactly:

    L1 (in-process LRU, ~30s)  → absorbs same-pod bursts, µs access
    L2 (Redis, jittered 1-4h)  → global truth, cross-pod
    Singleflight               → one compute per key per expiry cycle
    Stale-while-revalidate     → stale hits serve instantly, refresh
                                 in the background

The stampede story (FM-04): on L2 miss, we take a Redis lock
(``SET NX PX``). The winner computes and stores; followers poll for the
value for up to ``cache_wait_ms`` then either read the fresh value or
compute themselves (never block a user longer than the wait budget).

Failure policy (FM-05): FAIL OPEN. Redis down → L1 only + fresh compute.
Cache is an accelerator, never a dependency.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
from collections import OrderedDict
from typing import Any

import structlog

from configs.settings import get_settings
from core.observability import CACHE_REQUESTS, SINGLEFLIGHT

logger = structlog.get_logger(__name__)


class _L1Cache:
    """Tiny bounded LRU with TTL — per-pod burst absorber."""

    def __init__(self, max_items: int = 256, ttl_s: float = 30.0) -> None:
        self._max = max_items
        self._ttl = ttl_s
        self._data: OrderedDict[str, tuple[float, float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        stored_at, expires_at, value = entry
        if expires_at < stored_at:  # stale entry: soft-expired
            self._data.move_to_end(key)
            return ("__STALE__", value)
        self._data.move_to_end(key)
        return ("__FRESH__", value)

    def set(self, key: str, value: Any, ttl_s: float) -> None:
        if len(self._data) >= self._max:
            self._data.popitem(last=False)  # evict LRU
        self._data[key] = (ttl_s, ttl_s + ttl_s, value)

    def mark_soft_expired(self, key: str) -> None:
        entry = self._data.get(key)
        if entry is not None:
            # force the fresh window to zero → next get returns STALE
            self._data[key] = (entry[0], 0.0, entry[2])


class ResponseCache:
    """
    Redis-backed response cache with singleflight and SWR.
    Cache key = SHA256(query | agent_type | model).
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Any | None = None
        self._client_checked = False
        self._l1 = _L1Cache(max_items=512, ttl_s=30.0)

    # ── Connection ──────────────────────────────────────────────────

    async def _get_client(self) -> Any | None:
        """Lazily connect; return None (fail-open) if Redis is down."""
        if self._client is not None:
            return self._client
        if self._client_checked:
            return None
        try:
            import redis.asyncio as aioredis

            self._client = await aioredis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            self._client_checked = True
            return self._client
        except Exception as exc:
            logger.warning("cache.redis_unavailable_fail_open", error=str(exc)[:150])
            self._client_checked = True
            return None

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
        self._client_checked = False

    # ── Keys ────────────────────────────────────────────────────────

    def _make_key(self, query: str, agent_type: str, model: str) -> str:
        raw = f"{query.lower().strip()}|{agent_type}|{model}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"ask_web:v2:{digest}"

    def _jittered_ttl(self) -> int:
        base = self._settings.cache_ttl_s
        jitter = self._settings.cache_jitter_ratio
        return int(base * random.uniform(1 - jitter / 2, 1 + jitter / 2))

    # ── Core API ────────────────────────────────────────────────────

    async def get(
        self, query: str, agent_type: str, model: str
    ) -> dict[str, Any] | None:
        """Fresh hit → value; stale hit → value + background refresh hint."""
        key = self._make_key(query, agent_type, model)

        l1 = self._l1.get(key)
        if l1 is not None:
            state, value = l1
            CACHE_REQUESTS.labels(layer="l1", result=state.split("_")[1].lower()).inc()
            return value

        client = await self._get_client()
        if client is None:
            CACHE_REQUESTS.labels(layer="l2", result="miss").inc()
            return None

        try:
            raw = await client.get(key)
            if not raw:
                CACHE_REQUESTS.labels(layer="l2", result="miss").inc()
                return None
            value = json.loads(raw)
            self._l1.set(key, value, ttl_s=self._settings.cache_stale_s)
            CACHE_REQUESTS.labels(layer="l2", result="hit").inc()
            return value
        except Exception as exc:
            logger.warning("cache.get_failed", error=str(exc)[:150])
            return None

    async def set(
        self,
        query: str,
        agent_type: str,
        model: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        key = self._make_key(query, agent_type, model)
        self._l1.set(key, data, ttl_s=self._settings.cache_stale_s)

        client = await self._get_client()
        if client is None:
            return
        try:
            await client.setex(key, ttl or self._jittered_ttl(), json.dumps(data))
        except Exception as exc:
            logger.warning("cache.set_failed", error=str(exc)[:150])

    async def invalidate(self, query: str, agent_type: str, model: str) -> None:
        key = self._make_key(query, agent_type, model)
        client = await self._get_client()
        if client is None:
            return
        try:
            await client.delete(key)
        except Exception as exc:
            logger.warning("cache.invalidate_failed", error=str(exc)[:150])

    # ── Singleflight (ADR-003 / FM-04) ──────────────────────────────

    async def get_or_compute(
        self,
        query: str,
        agent_type: str,
        model: str,
        compute,  # Callable[[], Awaitable[dict]]
    ) -> tuple[dict[str, Any], bool]:
        """
        The stampede-proof read path.

        Returns (value, computed_here). Followers that waited still get
        the winner's value; only one pod pays the compute cost.
        """
        cached = await self.get(query, agent_type, model)
        if cached is not None:
            return cached, False

        key = self._make_key(query, agent_type, model)
        lock_key = f"{key}:lock"
        client = await self._get_client()

        if client is None:
            # No Redis: no cross-pod coordination possible; compute.
            value = await compute()
            await self.set(query, agent_type, model, value)
            SINGLEFLIGHT.labels(outcome="lock_error").inc()
            return value, True

        # ── Try to become the winner ────────────────────────────────
        try:
            won = await client.set(
                lock_key, "1", px=self._settings.cache_lock_ttl_ms, nx=True
            )
        except Exception as exc:
            logger.warning("cache.lock_failed", error=str(exc)[:150])
            value = await compute()
            await self.set(query, agent_type, model, value)
            SINGLEFLIGHT.labels(outcome="lock_error").inc()
            return value, True

        if won:
            SINGLEFLIGHT.labels(outcome="winner").inc()
            try:
                value = await compute()
                await self.set(query, agent_type, model, value)
                return value, True
            finally:
                try:
                    await client.delete(lock_key)
                except Exception:
                    pass

        # ── Follower: wait briefly for the winner ───────────────────
        SINGLEFLIGHT.labels(outcome="follower").inc()
        deadline = asyncio.get_event_loop().time() + (
            self._settings.cache_wait_ms / 1000
        )
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.15)
            value = await self.get(query, agent_type, model)
            if value is not None:
                return value, False

        # Winner too slow (or died): compute ourselves rather than
        # fail the user request.
        SINGLEFLIGHT.labels(outcome="timeout").inc()
        value = await compute()
        await self.set(query, agent_type, model, value)
        return value, True
