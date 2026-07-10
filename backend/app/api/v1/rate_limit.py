"""EMBEDHUNT AI — per-endpoint rate limiting.

A Redis-backed sliding-window counter (using a sorted set of request
timestamps) with a transparent in-process fallback for when Redis is
unavailable or in tests. Exposed as a FastAPI dependency factory so each route
can declare its own budget:

    dependencies=[Depends(rate_limit("mentor_chat", 20, 3600))]

When the limit is exceeded the dependency raises HTTP 429 with a body that
always carries ``retry_after_seconds`` so clients can back off precisely.
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Depends, HTTPException

from app.auth.permissions import get_current_user_id
from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

_KEY_PREFIX = "ratelimit"


class SlidingWindowLimiter:
    """Sliding-window request counter backed by Redis, memory as fallback."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis = None
        self._connected = False
        # Fallback store: full_key -> list[timestamp].
        self._mem: dict[str, list[float]] = {}

    async def _client(self):
        if self._connected:
            return self._redis
        self._connected = True
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(self._redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
        except Exception as exc:  # noqa: BLE001 — degrade to memory on any failure
            logger.warning("ratelimit_redis_unavailable", error=str(exc))
            self._redis = None
        return self._redis

    async def hit(self, key: str, max_calls: int, window_seconds: int) -> tuple[bool, int]:
        """Record a hit. Return ``(allowed, retry_after_seconds)``.

        ``retry_after_seconds`` is 0 when allowed, else the whole seconds until
        the oldest in-window request expires.
        """
        now = time.time()
        cutoff = now - window_seconds
        full_key = f"{_KEY_PREFIX}:{key}"
        client = await self._client()

        if client is not None:
            try:
                return await self._hit_redis(client, full_key, now, cutoff, max_calls, window_seconds)
            except Exception as exc:  # noqa: BLE001 — fall back to memory on redis error
                logger.warning("ratelimit_redis_error", error=str(exc))
        return self._hit_memory(full_key, now, cutoff, max_calls, window_seconds)

    async def _hit_redis(self, client, full_key, now, cutoff, max_calls, window_seconds):
        async with client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(full_key, 0, cutoff)
            pipe.zcard(full_key)
            _, count = (await pipe.execute())[:2]
        if count >= max_calls:
            oldest = await client.zrange(full_key, 0, 0, withscores=True)
            retry = window_seconds
            if oldest:
                retry = max(1, int(oldest[0][1] + window_seconds - now))
            return False, retry
        member = f"{now:.6f}"
        await client.zadd(full_key, {member: now})
        await client.expire(full_key, window_seconds)
        return True, 0

    def _hit_memory(self, full_key, now, cutoff, max_calls, window_seconds):
        hits = [t for t in self._mem.get(full_key, []) if t >= cutoff]
        if len(hits) >= max_calls:
            self._mem[full_key] = hits
            retry = max(1, int(hits[0] + window_seconds - now))
            return False, retry
        hits.append(now)
        self._mem[full_key] = hits
        return True, 0


# Single shared limiter instance across the process.
_limiter = SlidingWindowLimiter()


def rate_limit(name: str, max_calls: int, window_seconds: int) -> Callable:
    """Build a FastAPI dependency enforcing ``max_calls`` per ``window_seconds``
    per authenticated user for the named endpoint bucket."""

    async def _dependency(user_id: str = Depends(get_current_user_id)) -> str:
        allowed, retry_after = await _limiter.hit(f"{name}:{user_id}", max_calls, window_seconds)
        if not allowed:
            logger.warning("rate_limited", endpoint=name, user_id=user_id, retry_after=retry_after)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limited",
                    "message": f"Rate limit exceeded for {name}. Retry in {retry_after}s.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        return user_id

    return _dependency
