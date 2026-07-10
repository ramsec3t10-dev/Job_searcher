"""EMBEDHUNT AI — BedrockClient tests.

Covers retry-on-transient-error, circuit-breaker open after N failures, fallback
when open, and correct exception on timeout. The anthropic SDK is fully mocked
via ``_get_client`` so no network is touched; ``asyncio.sleep`` is patched so
retry backoff does not slow the suite.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm import bedrock_client as bc
from app.llm.bedrock_client import BedrockError, BedrockClient, CircuitOpenError
from app.llm.model_selector import TaskType


def _ok_response(text="hello", tin=10, tout=5):
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=tin, output_tokens=tout)
    return SimpleNamespace(content=[block], usage=usage)


def _client_with(side_effect):
    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=side_effect)
    return client


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(bc.asyncio, "sleep", AsyncMock())


@pytest.mark.asyncio
async def test_retry_on_transient_error_then_success():
    client = _client_with([RuntimeError("boom"), RuntimeError("boom2"), _ok_response("ok")])
    c = BedrockClient(api_key="k", max_retries=3)
    c._get_client = lambda: client

    result = await c.invoke_model("claude-haiku-4-5", [{"role": "user", "content": "hi"}])

    assert result["content"] == "ok"
    assert client.messages.create.await_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_five_failures():
    client = _client_with(RuntimeError("down"))
    c = BedrockClient(api_key="k", max_retries=1)
    c._get_client = lambda: client

    for _ in range(5):
        with pytest.raises(BedrockError):
            await c.invoke_model("claude-sonnet-4-6", [{"role": "user", "content": "x"}])

    # 6th call is short-circuited by the open breaker (no task → raises).
    with pytest.raises(CircuitOpenError):
        await c.invoke_model("claude-sonnet-4-6", [{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_circuit_breaker_returns_fallback_when_open():
    client = _client_with(RuntimeError("down"))
    c = BedrockClient(api_key="k", max_retries=1)
    c._get_client = lambda: client

    for _ in range(5):
        with pytest.raises(BedrockError):
            await c.invoke_model("claude-sonnet-4-6", [{"role": "user", "content": "x"}])

    # With a task supplied, an open circuit returns a graceful fallback.
    result = await c.invoke_model(
        "claude-sonnet-4-6", [{"role": "user", "content": "x"}], task=TaskType.MENTORING
    )
    assert result["fallback"] is True
    assert result["model"] == "fallback"


@pytest.mark.asyncio
async def test_timeout_raises_bedrock_error():
    client = _client_with(asyncio.TimeoutError())
    c = BedrockClient(api_key="k", max_retries=2)
    c._get_client = lambda: client

    with pytest.raises(BedrockError):
        await c.invoke_model("claude-haiku-4-5", [{"role": "user", "content": "x"}])
