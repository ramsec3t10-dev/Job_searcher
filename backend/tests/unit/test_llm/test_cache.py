"""Unit tests — semantic LLM cache (memory + fallback paths)."""
from app.llm.cache import SemanticCache, ttl_for
from app.llm.model_selector import TaskType
from app.llm.router import AIResponse


def _response() -> AIResponse:
    return AIResponse(
        content="hello",
        model_used="claude-haiku-4-5",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.001,
        latency_ms=12.0,
        cached=False,
        task_type=TaskType.EXTRACTION,
    )


def test_ttl_table():
    assert ttl_for(TaskType.EXTRACTION) == 3600
    assert ttl_for(TaskType.MATCHING) == 1800
    assert ttl_for(TaskType.MENTORING) == 0


def test_make_key_is_stable_and_scoped():
    a = SemanticCache.make_key(TaskType.EXTRACTION, "sys", "hello")
    b = SemanticCache.make_key(TaskType.EXTRACTION, "sys", "hello")
    c = SemanticCache.make_key(TaskType.EXTRACTION, "sys", "other")
    assert a == b
    assert a.startswith("llm:")
    assert a != c


async def test_set_then_get_hit_in_memory():
    cache = SemanticCache(force_memory=True)
    key = SemanticCache.make_key(TaskType.EXTRACTION, "s", "u")
    assert await cache.get(key) is None
    await cache.set(key, _response(), 3600)
    hit = await cache.get(key)
    assert hit is not None
    assert hit.content == "hello"
    assert hit.cached is True
    assert hit.task_type == TaskType.EXTRACTION


async def test_zero_ttl_is_never_cached():
    cache = SemanticCache(force_memory=True)
    key = "llm:never"
    await cache.set(key, _response(), 0)
    assert await cache.get(key) is None


async def test_invalidate_user_clears_keys():
    cache = SemanticCache(force_memory=True)
    key = SemanticCache.make_key(TaskType.MATCHING, "s", "u")
    await cache.set(key, _response(), 1800, user_id="u1")
    assert await cache.get(key) is not None
    await cache.invalidate_user("u1")
    assert await cache.get(key) is None


async def test_redis_unavailable_falls_back_to_memory():
    # Port 6390 is not expected to have a Redis server; the cache must still work.
    cache = SemanticCache(redis_url="redis://127.0.0.1:6390/0")
    key = "llm:fallback"
    await cache.set(key, _response(), 60)
    hit = await cache.get(key)
    assert hit is not None
    assert hit.content == "hello"
