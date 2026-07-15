"""EMBEDHUNT AI — Orchestrator cache engine (exact + semantic).

Two-tier cache keyed off the orchestrator ``task`` + ``payload``:

1. **Exact match** — ``sha256(task + normalized payload JSON)``.
2. **Semantic match** — on an exact miss, embed the payload's text and return the
   nearest previously-cached result for the same task whose cosine similarity
   clears ``ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD``. Embeddings come from
   :mod:`app.ai.embeddings`, which degrades to an offline deterministic model, so
   this works without heavy dependencies or network access.

Both tiers use Redis when reachable and fall back to an in-process store, so a
cache outage never breaks a request.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

from app.config.logging import get_logger
from app.config.settings import settings
from app.orchestrator.engine_base import EngineResult, InferenceEngine

logger = get_logger(__name__)

# Fallback TTL (seconds) for tasks not listed in ORCHESTRATOR_CACHE_TTL.
_DEFAULT_TTL = 86_400


def ttl_for(task: str) -> int:
    """Resolve the cache TTL (seconds) for ``task`` from settings.

    Tasks configured in ``ORCHESTRATOR_CACHE_TTL`` use their value; everything
    else falls back to :data:`_DEFAULT_TTL`. A TTL of 0 disables caching for the
    task (nothing is written).
    """
    table = getattr(settings, "ORCHESTRATOR_CACHE_TTL", None) or {}
    return int(table.get(task, _DEFAULT_TTL))


def _embedding_text(task: str, payload: dict) -> str:
    """Extract the natural-language text of a payload for embedding."""
    for key in ("prompt", "input", "query", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        joined = " ".join(
            m.get("content", "") for m in messages if isinstance(m, dict) and m.get("content")
        )
        if joined.strip():
            return joined
    return json.dumps(payload, sort_keys=True, default=str)


class CacheEngine(InferenceEngine):
    """Exact + semantic cache engine over Redis with an in-memory fallback."""

    def __init__(self, redis_url: Optional[str] = None, force_memory: bool = False):
        self._redis_url = redis_url or settings.REDIS_URL
        self._force_memory = force_memory
        self._redis = None
        self._connected = False
        # key -> (expiry_epoch_or_0, serialized EngineResult)
        self._mem: dict[str, tuple[float, str]] = {}
        # task -> list[(embedding, serialized EngineResult)] for semantic recall.
        self._emb_mem: dict[str, list[tuple[list[float], str]]] = {}
        self._embedder = None

    # ── keys / embedding ────────────────────────────────────────────────────
    @staticmethod
    def make_key(task: str, payload: dict) -> str:
        """Build a stable exact-match key from the task and normalized payload."""
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        raw = f"{task}|{normalized}"
        return "orch:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _emb_index_key(task: str) -> str:
        return "orch:emb:idx:" + hashlib.sha256(task.encode("utf-8")).hexdigest()

    def _embed(self, text: str) -> list[float]:
        if self._embedder is None:
            from app.ai.embeddings import get_embedding_engine

            self._embedder = get_embedding_engine()
        return self._embedder.embed_text(text)

    @property
    def _semantic_enabled(self) -> bool:
        return bool(getattr(settings, "ORCHESTRATOR_SEMANTIC_CACHE", True))

    @property
    def _semantic_threshold(self) -> float:
        return float(getattr(settings, "ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD", 0.92))

    @property
    def _semantic_cap(self) -> int:
        return int(getattr(settings, "ORCHESTRATOR_SEMANTIC_CACHE_MAX_PER_TASK", 500))

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
            logger.warning("orchestrator_cache_redis_unavailable", error=str(exc))
            self._redis = None
        return self._redis

    # ── read ────────────────────────────────────────────────────────────────
    async def run(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        """InferenceEngine entrypoint: return a cached EngineResult or ``None``."""
        key = self.make_key(task, payload)
        raw = None
        client = await self._client()
        if client is not None:
            try:
                raw = await client.get(key)
            except Exception:  # noqa: BLE001 — treat any Redis error as a miss
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
            # Exact-match miss → try the semantic (embedding-similarity) tier.
            return await self.semantic_lookup(task, payload)
        result = EngineResult.model_validate_json(raw)
        result.cached = True
        logger.info("orchestrator_cache_hit", task=task, kind="exact")
        return result

    async def semantic_lookup(self, task: str, payload: dict) -> Optional[EngineResult]:
        """Return the nearest cached result for ``task`` above the threshold.

        Embeds the payload text and cosine-compares against previously-cached
        results for the same task. Returns ``None`` when semantic caching is off,
        nothing is stored, or nothing clears the similarity threshold.
        """
        if not self._semantic_enabled:
            return None
        try:
            query = self._embed(_embedding_text(task, payload))
        except Exception as exc:  # noqa: BLE001 — semantic cache must never break a call
            logger.warning("orchestrator_semantic_embed_failed", error=str(exc))
            return None

        best_sim = self._semantic_threshold
        best_blob: Optional[str] = None
        async for embedding, blob in self._iter_embeddings(task):
            sim = _cosine(query, embedding)
            if sim >= best_sim:
                best_sim = sim
                best_blob = blob
        if best_blob is None:
            return None
        result = EngineResult.model_validate_json(best_blob)
        result.cached = True
        logger.info("orchestrator_cache_hit", task=task, kind="semantic", similarity=round(best_sim, 4))
        return result

    async def _iter_embeddings(self, task: str):
        """Yield ``(embedding, blob)`` for every semantic entry stored for ``task``."""
        seen = 0
        client = await self._client()
        if client is not None:
            try:
                members = await client.smembers(self._emb_index_key(task))
                for entry_key in members or []:
                    raw = await client.get(entry_key)
                    if not raw:
                        continue
                    data = json.loads(raw)
                    seen += 1
                    yield data["embedding"], data["blob"]
            except Exception:  # noqa: BLE001
                pass
        if seen:
            return
        for embedding, blob in self._emb_mem.get(task, []):
            yield embedding, blob

    # ── write ───────────────────────────────────────────────────────────────
    async def set(self, task: str, payload: dict, result: EngineResult) -> None:
        """Write ``result`` back to both cache tiers, honouring the TTL."""
        ttl = ttl_for(task)
        if ttl == 0:
            return
        key = self.make_key(task, payload)
        blob = result.model_copy(update={"cached": True}).model_dump_json()
        client = await self._client()
        if client is not None:
            try:
                await client.set(key, blob, ex=ttl if ttl > 0 else None)
            except Exception:  # noqa: BLE001 — cache writes are best-effort
                pass
        self._mem[key] = (time.time() + ttl if ttl > 0 else 0, blob)
        if self._semantic_enabled:
            await self._store_embedding(task, payload, blob, ttl, key)

    async def _store_embedding(self, task: str, payload: dict, blob: str, ttl: int, key: str) -> None:
        try:
            embedding = self._embed(_embedding_text(task, payload))
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.warning("orchestrator_semantic_embed_failed", error=str(exc))
            return
        entry_key = "orch:emb:" + key.split(":")[-1]
        cap = self._semantic_cap
        client = await self._client()
        if client is not None:
            try:
                index_key = self._emb_index_key(task)
                await client.set(
                    entry_key,
                    json.dumps({"embedding": embedding, "blob": blob}),
                    ex=ttl if ttl > 0 else None,
                )
                await client.sadd(index_key, entry_key)
                # Bound the index: trim excess members (also drop their payloads).
                over = await client.scard(index_key) - cap
                if over > 0:
                    excess = await client.spop(index_key, over)
                    excess = list(excess) if isinstance(excess, (set, list, tuple)) else [excess]
                    if excess:
                        await client.delete(*excess)
                return
            except Exception:  # noqa: BLE001
                pass
        bucket = self._emb_mem.setdefault(task, [])
        bucket.append((embedding, blob))
        if len(bucket) > cap:  # keep the newest `cap` entries
            del bucket[: len(bucket) - cap]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
