"""EMBEDHUNT AI — Semantic LLM Cache.

Caches AIResponse objects keyed by (task, system prompt, user message). Uses
Redis when reachable and transparently falls back to an in-memory store when
Redis is unavailable, so the layer never hard-fails on a cache outage.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict
from typing import Optional, TYPE_CHECKING

from app.config.logging import get_logger
from app.config.settings import settings
from app.llm.model_selector import TaskType

if TYPE_CHECKING:
    from app.llm.router import AIResponse

logger = get_logger(__name__)

# Per-task TTL (seconds). 0 means never cache (e.g. personalised advice).
_TTL: dict[TaskType, int] = {
    TaskType.EXTRACTION: 3600,
    TaskType.MATCHING: 1800,
    TaskType.MENTORING: 0,
}


def ttl_for(task: TaskType) -> int:
    return _TTL.get(task, settings.LLM_CACHE_TTL_SECONDS)


class SemanticCache:
    def __init__(self, redis_url: Optional[str] = None, force_memory: bool = False):
        self._redis_url = redis_url or settings.REDIS_URL
        self._force_memory = force_memory
        self._redis = None
        self._connected = False
        self._mem: dict[str, tuple[float, str]] = {}
        self._user_index: dict[str, set[str]] = {}
        # Embedding cache: key -> (embedding, serialized AIResponse).
        self._emb_mem: dict[str, tuple[list[float], str]] = {}

    @staticmethod
    def make_key(task: TaskType, system: str, user_message: str) -> str:
        raw = f"{task.value}|{system or ''}|{user_message or ''}"
        return "llm:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _client(self):
        if self._force_memory:
            return None
        if self._connected:
            return self._redis
        self._connected = True
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(self._redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
        except Exception as exc:  # noqa: BLE001 — degrade to memory on any failure
            logger.warning("llm_cache_redis_unavailable", error=str(exc))
            self._redis = None
        return self._redis

    async def get(self, key: str) -> Optional["AIResponse"]:
        raw = None
        client = await self._client()
        if client is not None:
            try:
                raw = await client.get(key)
            except Exception:  # noqa: BLE001
                raw = None
        if raw is None:
            item = self._mem.get(key)
            if item is not None:
                expiry, value = item
                if expiry == 0 or expiry > time.time():
                    raw = value
                else:
                    self._mem.pop(key, None)
        if raw is None:
            return None
        return self._deserialize(raw)

    async def set(self, key: str, response: "AIResponse", ttl: int, user_id: Optional[str] = None) -> None:
        if ttl == 0:
            return
        payload = self._serialize(response)
        client = await self._client()
        if client is not None:
            try:
                await client.set(key, payload, ex=ttl if ttl > 0 else None)
                if user_id:
                    await client.sadd(f"llm:user:{user_id}", key)
            except Exception:  # noqa: BLE001
                pass
        self._mem[key] = (time.time() + ttl if ttl > 0 else 0, payload)
        if user_id:
            self._user_index.setdefault(user_id, set()).add(key)

    async def invalidate_user(self, user_id: str) -> None:
        client = await self._client()
        if client is not None:
            try:
                index_key = f"llm:user:{user_id}"
                keys = await client.smembers(index_key)
                if keys:
                    await client.delete(*keys)
                await client.delete(index_key)
            except Exception:  # noqa: BLE001
                pass
        for key in self._user_index.pop(user_id, set()):
            self._mem.pop(key, None)

    # ── Embedding-similarity cache (mentor conversations) ─────────────────
    _EMB_INDEX = "llm:emb:index"

    @staticmethod
    def _emb_key(key: str) -> str:
        return f"llm:emb:{key}"

    async def store_with_embedding(
        self, key: str, response: "AIResponse", embedding: list[float]
    ) -> None:
        """Persist a response alongside its query embedding for fuzzy recall.

        Used for open-ended tasks (e.g. mentoring) where two differently phrased
        questions should hit the same cached answer.
        """
        if not embedding:
            return
        serialized = self._serialize(response)
        payload = json.dumps({"embedding": list(embedding), "response": serialized})
        entry_key = self._emb_key(key)
        client = await self._client()
        if client is not None:
            try:
                await client.set(entry_key, payload)
                await client.sadd(self._EMB_INDEX, entry_key)
            except Exception:  # noqa: BLE001
                pass
        self._emb_mem[entry_key] = (list(embedding), serialized)

    async def find_similar(
        self, query_embedding: list[float], threshold: float = 0.92
    ) -> Optional["AIResponse"]:
        """Return the cached response whose stored query embedding is closest to
        ``query_embedding``, provided that similarity exceeds ``threshold``.
        """
        if not query_embedding:
            return None
        best_sim = threshold
        best_raw: Optional[str] = None

        async for embedding, raw in self._iter_embeddings():
            sim = self._cosine(query_embedding, embedding)
            if sim >= best_sim:
                best_sim = sim
                best_raw = raw
        if best_raw is None:
            return None
        logger.info("ai_cache_semantic_hit", similarity=round(best_sim, 4))
        response = self._deserialize(best_raw)
        response.cached = True
        return response

    async def _iter_embeddings(self):
        """Yield ``(embedding, serialized_response)`` for every stored entry."""
        seen: set[str] = set()
        client = await self._client()
        if client is not None:
            try:
                entry_keys = await client.smembers(self._EMB_INDEX)
                for entry_key in entry_keys or []:
                    raw = await client.get(entry_key)
                    if not raw:
                        continue
                    data = json.loads(raw)
                    seen.add(entry_key)
                    yield data["embedding"], data["response"]
            except Exception:  # noqa: BLE001
                pass
        for entry_key, (embedding, raw) in self._emb_mem.items():
            if entry_key not in seen:
                yield embedding, raw

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _serialize(self, response: "AIResponse") -> str:
        data = asdict(response)
        task = response.task_type
        data["task_type"] = task.value if hasattr(task, "value") else str(task)
        return json.dumps(data)

    def _deserialize(self, raw: str) -> "AIResponse":
        from app.llm.router import AIResponse

        data = json.loads(raw)
        data["task_type"] = TaskType(data["task_type"])
        data["cached"] = True
        return AIResponse(**data)
