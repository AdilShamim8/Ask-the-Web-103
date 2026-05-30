from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from configs.settings import get_settings

logger = structlog.get_logger(__name__)

_TTL_SECONDS = 3600  # 1 hour cache


class ResponseCache:
    """
    Redis-backed response cache.
    Cache key = SHA256(query + agent_type + model).
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = await aioredis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    def _make_key(self, query: str, agent_type: str, model: str) -> str:
        raw = f"{query.lower().strip()}|{agent_type}|{model}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"ask_web:v1:{digest}"

    async def get(
        self, query: str, agent_type: str, model: str
    ) -> dict[str, Any] | None:
        try:
            client = await self._get_client()
            key = self._make_key(query, agent_type, model)
            raw = await client.get(key)
            if raw:
                logger.debug("cache.hit", key=key[:16])
                return json.loads(raw)
            logger.debug("cache.miss", key=key[:16])
            return None
        except Exception as exc:
            logger.warning("cache.get_failed", error=str(exc))
            return None

    async def set(
        self,
        query: str,
        agent_type: str,
        model: str,
        data: dict[str, Any],
        ttl: int = _TTL_SECONDS,
    ) -> None:
        try:
            client = await self._get_client()
            key = self._make_key(query, agent_type, model)
            await client.setex(key, ttl, json.dumps(data))
            logger.debug("cache.set", key=key[:16], ttl=ttl)
        except Exception as exc:
            logger.warning("cache.set_failed", error=str(exc))

    async def invalidate(
        self, query: str, agent_type: str, model: str
    ) -> None:
        try:
            client = await self._get_client()
            key = self._make_key(query, agent_type, model)
            await client.delete(key)
        except Exception as exc:
            logger.warning("cache.invalidate_failed", error=str(exc))

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None