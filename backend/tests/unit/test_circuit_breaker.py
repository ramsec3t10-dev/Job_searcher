"""Unit tests — Circuit breaker & graceful degradation (Part F)."""
import pytest

from app.llm.bedrock_client import (
    BedrockClient,
    CircuitOpenError,
    _CircuitBreaker,
    circuit_state,
    fallback_for,
)
from app.llm.model_selector import TaskType


def test_breaker_opens_after_threshold_failures():
    b = _CircuitBreaker(threshold=5, window_seconds=60, reset_seconds=60)
    assert b.allow()
    for _ in range(5):
        b.record_failure()
    assert b.state() == "open"
    assert not b.allow()


def test_breaker_closes_on_success():
    b = _CircuitBreaker(threshold=2, window_seconds=60, reset_seconds=60)
    b.record_failure()
    b.record_failure()
    assert b.state() == "open"
    b.record_success()
    assert b.state() == "closed"
    assert b.allow()


def test_breaker_half_opens_after_reset():
    b = _CircuitBreaker(threshold=2, window_seconds=60, reset_seconds=1)
    b.record_failure()
    b.record_failure()
    assert b.state() == "open"
    # Simulate the reset window elapsing.
    b.opened_at -= 2
    assert b.allow() is True  # a single probe is permitted
    assert b.state() == "half_open"


def test_old_failures_outside_window_do_not_open():
    b = _CircuitBreaker(threshold=3, window_seconds=60, reset_seconds=60)
    # Two stale failures (older than the window) then one fresh failure.
    b.record_failure()
    b.record_failure()
    b._failures = [t - 120 for t in b._failures]  # age them out of the window
    b.record_failure()
    assert b.state() == "closed"


def test_state_change_updates_global_hook():
    b = _CircuitBreaker(threshold=1, window_seconds=60, reset_seconds=60)
    b.record_failure()
    assert circuit_state() == "open"
    b.record_success()
    assert circuit_state() == "closed"


def test_fallback_for_known_tasks():
    assert fallback_for(TaskType.EXTRACTION)["content"] == "{}"
    assert "unavailable" in fallback_for(TaskType.MENTORING)["content"].lower()
    assert fallback_for(None) is None


async def test_open_circuit_returns_fallback_with_task():
    client = BedrockClient()
    for _ in range(5):
        client._breaker.record_failure()
    result = await client.invoke_model(
        "anthropic.haiku", [{"role": "user", "content": "hi"}], task=TaskType.MENTORING
    )
    assert result["fallback"] is True
    assert "unavailable" in result["content"].lower()


async def test_open_circuit_raises_without_task():
    client = BedrockClient()
    for _ in range(5):
        client._breaker.record_failure()
    with pytest.raises(CircuitOpenError):
        await client.invoke_model("anthropic.haiku", [{"role": "user", "content": "hi"}])
