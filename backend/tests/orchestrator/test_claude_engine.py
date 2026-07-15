"""EMBEDHUNT AI — Claude engine adapter tests.

Wraps a mocked AIRouter (no Bedrock) to verify task→TaskType mapping, message
construction from the payload, and the AIResponse → EngineResult adaptation.
"""
from unittest.mock import AsyncMock, MagicMock

from app.llm.model_selector import TaskType
from app.llm.router import AIResponse
from app.orchestrator.claude_engine import ClaudeEngine


def _ai_response(content: str = "hi", cached: bool = False) -> AIResponse:
    return AIResponse(
        content=content,
        model_used="claude-sonnet-4-6",
        input_tokens=1,
        output_tokens=2,
        cost_usd=0.003,
        latency_ms=5.0,
        cached=cached,
        task_type=TaskType.SUMMARIZATION,
    )


def _engine(response: AIResponse | None = None) -> tuple[ClaudeEngine, MagicMock]:
    router = MagicMock()
    router.route = AsyncMock(return_value=response or _ai_response())
    return ClaudeEngine(router=router), router


async def test_wraps_router_response_as_engine_result():
    engine, router = _engine()
    result = await engine.run("summarization", {"prompt": "hello"})

    assert result.text == "hi"
    assert result.engine_used == "claude:claude-sonnet-4-6"
    assert result.confidence is None
    assert result.cost_estimate_usd == 0.003
    assert result.cached is False


async def test_task_string_maps_to_tasktype():
    engine, router = _engine()
    await engine.run("summarization", {"prompt": "x"})
    assert router.route.await_args.args[0] == TaskType.SUMMARIZATION


async def test_unknown_task_falls_back_to_default_tasktype():
    engine, router = _engine()
    await engine.run("some_unmapped_task", {"prompt": "x"})
    assert router.route.await_args.args[0] == TaskType.SUMMARIZATION


async def test_prompt_payload_becomes_user_message():
    engine, router = _engine()
    await engine.run("matching", {"prompt": "match this"})
    messages = router.route.await_args.args[1]
    assert messages == [{"role": "user", "content": "match this"}]


async def test_ready_messages_are_passed_through():
    engine, router = _engine()
    msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    await engine.run("mentoring", {"messages": msgs})
    assert router.route.await_args.args[1] == msgs


async def test_router_cached_flag_propagates():
    engine, _ = _engine(_ai_response(cached=True))
    result = await engine.run("summarization", {"prompt": "x"})
    assert result.cached is True
