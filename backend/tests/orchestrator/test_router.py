"""EMBEDHUNT AI — Orchestrator routing tests.

Exercise the fallthrough order (rule → cache → [local model: Phase 3] → claude)
with mocked engines so no Redis or Bedrock is touched. Verifies that rule tasks
and cache hits never reach Claude, and that fresh Claude results are written
back to the cache.
"""
from unittest.mock import AsyncMock, MagicMock

from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.rule_engine import RuleEngine
from app.orchestrator.router import Orchestrator


def _claude_result(text: str = "from-claude") -> EngineResult:
    return EngineResult(
        text=text,
        engine_used="claude:mock",
        confidence=None,
        cached=False,
        cost_estimate_usd=0.01,
    )


def _mock_claude(result: EngineResult | None = None) -> MagicMock:
    claude = MagicMock(spec=ClaudeEngine)
    claude.run = AsyncMock(return_value=result or _claude_result())
    return claude


async def test_rule_task_never_reaches_claude():
    """A registered rule task is served by the rule engine, not Claude."""
    claude = _mock_claude()
    orch = Orchestrator(
        rule_engine=RuleEngine(),
        cache_engine=CacheEngine(force_memory=True),
        claude_engine=claude,
    )

    result = await orch.handle("daily_brief", {"name": "Ada", "streak_days": 3})

    assert result.engine_used == "rule:daily_brief"
    assert result.cost_estimate_usd == 0.0
    claude.run.assert_not_awaited()


async def test_cache_hit_skips_claude_on_second_call():
    """The second identical call is served from cache without calling Claude."""
    claude = _mock_claude(_claude_result("expensive"))
    orch = Orchestrator(
        rule_engine=RuleEngine(),
        cache_engine=CacheEngine(force_memory=True),
        claude_engine=claude,
    )
    task, payload = "summarization", {"prompt": "summarize me"}

    first = await orch.handle(task, payload)
    assert first.cached is False
    assert claude.run.await_count == 1

    second = await orch.handle(task, payload)
    assert second.cached is True
    assert second.text == "expensive"
    # Claude was NOT called again — the cache served the second request.
    assert claude.run.await_count == 1


async def test_fallthrough_order_all_engines_mocked():
    """rule → cache → claude, with a fresh claude result written back to cache."""
    rule = MagicMock(spec=RuleEngine)
    rule.run = AsyncMock(return_value=None)
    cache = MagicMock(spec=CacheEngine)
    cache.run = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    claude = _mock_claude()

    orch = Orchestrator(rule_engine=rule, cache_engine=cache, claude_engine=claude)
    result = await orch.handle("matching", {"prompt": "x"})

    rule.run.assert_awaited_once()
    cache.run.assert_awaited_once()
    claude.run.assert_awaited_once()
    cache.set.assert_awaited_once()  # fresh Claude result written back
    assert result.engine_used == "claude:mock"


async def test_rule_short_circuits_cache_and_claude():
    """A rule hit returns before the cache or Claude are ever consulted."""
    rule = MagicMock(spec=RuleEngine)
    rule.run = AsyncMock(
        return_value=EngineResult(text="r", engine_used="rule:x", cost_estimate_usd=0.0)
    )
    cache = MagicMock(spec=CacheEngine)
    cache.run = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    claude = _mock_claude()

    orch = Orchestrator(rule_engine=rule, cache_engine=cache, claude_engine=claude)
    result = await orch.handle("x", {})

    assert result.engine_used == "rule:x"
    cache.run.assert_not_awaited()
    claude.run.assert_not_awaited()
    cache.set.assert_not_awaited()


async def test_cache_hit_short_circuits_claude_and_no_writeback():
    """A cache hit returns Claude's earlier answer without re-calling or re-writing."""
    rule = MagicMock(spec=RuleEngine)
    rule.run = AsyncMock(return_value=None)
    cache = MagicMock(spec=CacheEngine)
    cache.run = AsyncMock(
        return_value=EngineResult(text="c", engine_used="claude:mock", cached=True)
    )
    cache.set = AsyncMock()
    claude = _mock_claude()

    orch = Orchestrator(rule_engine=rule, cache_engine=cache, claude_engine=claude)
    result = await orch.handle("matching", {"prompt": "x"})

    assert result.cached is True
    claude.run.assert_not_awaited()
    cache.set.assert_not_awaited()


async def test_cache_disabled_skips_cache_layer():
    """With caching off, the cache engine is never read or written."""
    rule = MagicMock(spec=RuleEngine)
    rule.run = AsyncMock(return_value=None)
    cache = MagicMock(spec=CacheEngine)
    cache.run = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    claude = _mock_claude()

    orch = Orchestrator(rule_engine=rule, cache_engine=cache, claude_engine=claude)
    orch._cache_enabled = False
    await orch.handle("matching", {"prompt": "x"})

    cache.run.assert_not_awaited()
    cache.set.assert_not_awaited()
    claude.run.assert_awaited_once()
