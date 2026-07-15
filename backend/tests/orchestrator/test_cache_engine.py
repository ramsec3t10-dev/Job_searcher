"""EMBEDHUNT AI — Orchestrator cache engine tests.

Uses the in-memory fallback (force_memory / an unreachable Redis) so no live
Redis is required. Covers key stability/normalisation, set→get round-trips, the
semantic-lookup stub, and TTL resolution from settings.
"""
from app.orchestrator.cache_engine import CacheEngine, ttl_for
from app.orchestrator.engine_base import EngineResult


def _result() -> EngineResult:
    return EngineResult(
        text="cached-text",
        engine_used="claude:mock",
        confidence=None,
        cached=False,
        cost_estimate_usd=0.02,
    )


def test_make_key_is_stable_and_order_independent():
    a = CacheEngine.make_key("matching", {"b": 2, "a": 1})
    b = CacheEngine.make_key("matching", {"a": 1, "b": 2})  # different insertion order
    c = CacheEngine.make_key("matching", {"a": 1, "b": 3})
    assert a == b  # normalised payload → same key regardless of key order
    assert a.startswith("orch:")
    assert a != c


def test_make_key_scoped_by_task():
    same_payload = {"x": 1}
    assert CacheEngine.make_key("matching", same_payload) != CacheEngine.make_key(
        "summarization", same_payload
    )


async def test_miss_then_set_then_hit_in_memory():
    cache = CacheEngine(force_memory=True)
    task, payload = "summarization", {"prompt": "hello"}

    assert await cache.run(task, payload) is None  # miss

    await cache.set(task, payload, _result())
    hit = await cache.run(task, payload)

    assert hit is not None
    assert hit.text == "cached-text"
    assert hit.cached is True  # served-from-cache flag flipped on read
    assert hit.cost_estimate_usd == 0.02


async def test_zero_ttl_is_never_cached():
    cache = CacheEngine(force_memory=True)
    task, payload = "no_cache_task", {"a": 1}
    # ttl_for falls back to the default; force TTL 0 via settings override.
    from app.config.settings import settings

    original = settings.ORCHESTRATOR_CACHE_TTL
    settings.ORCHESTRATOR_CACHE_TTL = {"no_cache_task": 0}
    try:
        await cache.set(task, payload, _result())
        assert await cache.run(task, payload) is None
    finally:
        settings.ORCHESTRATOR_CACHE_TTL = original


async def test_redis_unavailable_falls_back_to_memory():
    # Port 6390 is not expected to have Redis; the cache must still round-trip.
    cache = CacheEngine(redis_url="redis://127.0.0.1:6390/0")
    task, payload = "matching", {"prompt": "x"}
    await cache.set(task, payload, _result())
    hit = await cache.run(task, payload)
    assert hit is not None
    assert hit.text == "cached-text"


async def test_semantic_lookup_empty_store_returns_none():
    cache = CacheEngine(force_memory=True)
    assert await cache.semantic_lookup("matching", {"prompt": "x"}) is None


# The default 0.92 threshold is tuned for the production sentence-transformer
# model; these tests run against the offline fallback embedder, so they set a
# threshold matched to it to validate the mechanism (near-duplicate ≈ 0.88).
def _relax_threshold(value: float = 0.85):
    from app.config.settings import settings

    original = settings.ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD
    settings.ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD = value
    return settings, original


async def test_semantic_cache_hits_near_duplicate_payload():
    settings, original = _relax_threshold()
    try:
        cache = CacheEngine(force_memory=True)
        task = "company_summary"
        await cache.set(task, {"prompt": "Summarize the company Acme Robotics for a candidate."}, _result())

        # A near-identical (not byte-identical) payload misses the exact key but
        # should be served from the semantic tier.
        hit = await cache.run(task, {"prompt": "Summarize the company Acme Robotics for candidates."})
        assert hit is not None
        assert hit.text == "cached-text"
        assert hit.cached is True
    finally:
        settings.ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD = original


async def test_semantic_cache_misses_unrelated_payload():
    settings, original = _relax_threshold()
    try:
        cache = CacheEngine(force_memory=True)
        task = "company_summary"
        await cache.set(task, {"prompt": "Summarize the company Acme Robotics for a candidate."}, _result())

        miss = await cache.run(task, {"prompt": "Explain the RTOS scheduling algorithm in detail."})
        assert miss is None
    finally:
        settings.ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD = original


async def test_semantic_cache_can_be_disabled():
    from app.config.settings import settings

    original = settings.ORCHESTRATOR_SEMANTIC_CACHE
    settings.ORCHESTRATOR_SEMANTIC_CACHE = False
    try:
        cache = CacheEngine(force_memory=True)
        await cache.set("company_summary", {"prompt": "Summarize Acme Robotics for a candidate."}, _result())
        # Exact miss + semantic disabled → no hit.
        assert await cache.run("company_summary", {"prompt": "Summarize Acme Robotics for candidates."}) is None
    finally:
        settings.ORCHESTRATOR_SEMANTIC_CACHE = original


async def test_semantic_index_is_bounded():
    from app.config.settings import settings

    orig = settings.ORCHESTRATOR_SEMANTIC_CACHE_MAX_PER_TASK
    settings.ORCHESTRATOR_SEMANTIC_CACHE_MAX_PER_TASK = 3
    try:
        cache = CacheEngine(force_memory=True)
        for i in range(10):  # write far more than the cap
            await cache.set("company_summary", {"prompt": f"summarize company number {i}"}, _result())
        # In-memory embedding index is trimmed to the cap (newest kept).
        assert len(cache._emb_mem["company_summary"]) == 3
    finally:
        settings.ORCHESTRATOR_SEMANTIC_CACHE_MAX_PER_TASK = orig


def test_ttl_for_uses_settings_and_default():
    from app.config.settings import settings

    original = settings.ORCHESTRATOR_CACHE_TTL
    settings.ORCHESTRATOR_CACHE_TTL = {"matching": 1800}
    try:
        assert ttl_for("matching") == 1800
        assert ttl_for("unlisted_task") == 86_400  # 1-day default fallback
    finally:
        settings.ORCHESTRATOR_CACHE_TTL = original
