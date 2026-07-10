"""Unit tests — Cost optimization (Part C).

Verify prompt compression fires only for expensive models above the token
threshold, that savings are tracked, and that the cache-hit counter works.
"""
from app.llm.cost_tracker import CostTracker
from app.llm.model_selector import TaskType, select_model
from app.llm.router import AIRouter, estimate_tokens


class _FakeBedrock:
    def __init__(self):
        self.calls = 0

    async def invoke_model(self, model_id, messages, **kwargs):
        self.calls += 1
        return {
            "content": "COMPRESSED",
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 0.0,
            "model": model_id,
        }


def _router(bedrock):
    return AIRouter(bedrock_client=bedrock)


async def test_no_compression_below_threshold():
    fb = _FakeBedrock()
    router = _router(fb)
    cfg = select_model(TaskType.MATCHING)  # sonnet (expensive)
    prompt = "a" * 100
    out = await router.compress_if_needed(prompt, cfg)
    assert out == prompt
    assert fb.calls == 0


async def test_compression_triggers_for_expensive_long_prompt():
    fb = _FakeBedrock()
    router = _router(fb)
    cfg = select_model(TaskType.MATCHING)  # sonnet
    prompt = "word " * 7000  # ~3500 tokens, above the 3000 threshold
    assert estimate_tokens(prompt) > 3000
    out = await router.compress_if_needed(prompt, cfg)
    assert out == "COMPRESSED"
    assert fb.calls == 1
    assert router.cost_tracker.tokens_saved_by_compression > 0
    assert router.cost_tracker.estimated_savings_usd > 0


async def test_no_compression_for_cheap_model():
    fb = _FakeBedrock()
    router = _router(fb)
    cfg = select_model(TaskType.EXTRACTION)  # haiku (cheap)
    prompt = "word " * 7000
    out = await router.compress_if_needed(prompt, cfg)
    assert out == prompt  # cheap models are never compressed
    assert fb.calls == 0


def test_estimate_tokens_scales_with_length():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 4000) == 1000


def test_cost_tracker_records_cache_hit():
    tracker = CostTracker()
    tracker.record_cache_hit(0.01)
    tracker.record_cache_hit()
    stats = tracker.optimization_stats()
    assert stats["cache_hits"] == 2
    assert stats["estimated_savings_usd"] >= 0.01
