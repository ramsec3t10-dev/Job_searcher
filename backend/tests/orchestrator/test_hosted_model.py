"""EMBEDHUNT AI — Hosted open-model engine + routing/cost tests.

No network and no Postgres: the Together AI call (`_chat_completion`) is
monkeypatched, and cost-log persistence runs against in-memory SQLite. Covers
task-type gating, confidence-threshold escalation, the PII sanitizer, the v1
confidence heuristic, and AiUsageLog cost logging.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM tables
from app.database.base import Base
from app.models.orchestrator_usage import AiUsageLog
from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.hosted_model_engine import HostedModelEngine
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine
from app.orchestrator.router import Orchestrator
from app.orchestrator.rule_engine import RuleEngine
from app.orchestrator import task_registry


# ── fixtures / helpers ──────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


def _kg_none():
    kg = MagicMock(spec=KnowledgeGraphEngine)
    kg.run = AsyncMock(return_value=None)
    return kg


def _mock_claude(tokens_in=200, tokens_out=100, cost=0.01):
    claude = MagicMock(spec=ClaudeEngine)
    claude.run = AsyncMock(
        return_value=EngineResult(
            text="from-claude", engine_used="claude:mock", cost_estimate_usd=cost,
            tokens_in=tokens_in, tokens_out=tokens_out,
        )
    )
    return claude


def _hosted_returning(result):
    hosted = MagicMock(spec=HostedModelEngine)
    hosted.run = AsyncMock(return_value=result)
    return hosted


def _orch(hosted, claude, cache=None):
    return Orchestrator(
        rule_engine=RuleEngine(),
        knowledge_graph_engine=_kg_none(),
        cache_engine=cache or CacheEngine(force_memory=True),
        hosted_model_engine=hosted,
        claude_engine=claude,
    )


# ── task-type gating ────────────────────────────────────────────────────────
def test_task_registry_lists_are_explicit_and_disjoint():
    assert task_registry.is_hosted_allowed("skill_extraction")
    assert task_registry.is_hosted_allowed("resume_parsing")
    assert not task_registry.is_hosted_allowed("resume_rewrite")
    assert task_registry.is_claude_only("mentor_chat")
    # Allowlist semantics: an unrecognised task is not hosted-eligible.
    assert not task_registry.is_hosted_allowed("some_unknown_task")
    assert not (task_registry.HOSTED_MODEL_ALLOWED_TASKS & task_registry.CLAUDE_ONLY_TASKS)


@pytest.mark.parametrize(
    "task", ["resume_rewrite", "mentor_chat", "interview_evaluation", "negotiation_advice", "gap_analysis_explanation"]
)
async def test_claude_only_tasks_never_call_hosted(task):
    hosted = MagicMock(spec=HostedModelEngine)
    hosted.run = AsyncMock()
    claude = _mock_claude()
    orch = _orch(hosted, claude)

    result = await orch.handle(task, {"prompt": "x"})

    hosted.run.assert_not_awaited()  # restricted task bypasses the hosted model
    claude.run.assert_awaited_once()
    assert result.engine_used == "claude:mock"


async def test_unknown_task_skips_hosted():
    hosted = MagicMock(spec=HostedModelEngine)
    hosted.run = AsyncMock()
    claude = _mock_claude()
    orch = _orch(hosted, claude)

    await orch.handle("totally_unlisted_task", {"prompt": "x"})

    hosted.run.assert_not_awaited()
    claude.run.assert_awaited_once()


async def test_allowed_task_attempts_hosted_and_short_circuits():
    hosted = _hosted_returning(
        EngineResult(
            text="parsed", engine_used="together:llama", confidence=0.95,
            cost_estimate_usd=0.0001, tokens_in=100, tokens_out=50,
        )
    )
    claude = _mock_claude()
    orch = _orch(hosted, claude)

    result = await orch.handle("skill_extraction", {"prompt": "extract skills"})

    hosted.run.assert_awaited_once()
    claude.run.assert_not_awaited()  # confident hosted answer wins — no Claude call
    assert result.engine_used == "together:llama"


async def test_hosted_disabled_flag_skips_hosted():
    hosted = MagicMock(spec=HostedModelEngine)
    hosted.run = AsyncMock()
    claude = _mock_claude()
    orch = _orch(hosted, claude)
    orch._hosted_enabled = False

    await orch.handle("skill_extraction", {"prompt": "x"})

    hosted.run.assert_not_awaited()
    claude.run.assert_awaited_once()


# ── confidence-threshold escalation ─────────────────────────────────────────
async def test_low_confidence_escalates_to_claude():
    # Engine signalled escalation via confidence=None (still billed).
    hosted = _hosted_returning(
        EngineResult(
            text="", engine_used="together:llama", confidence=None,
            cost_estimate_usd=0.00005, tokens_in=80, tokens_out=10,
        )
    )
    claude = _mock_claude()
    orch = _orch(hosted, claude)

    result = await orch.handle("company_summary", {"prompt": "summarize"})

    hosted.run.assert_awaited_once()
    claude.run.assert_awaited_once()
    assert result.engine_used == "claude:mock"


async def test_hosted_none_result_escalates_to_claude():
    # Engine returned None entirely (disabled / API error).
    hosted = _hosted_returning(None)
    claude = _mock_claude()
    orch = _orch(hosted, claude)

    result = await orch.handle("company_summary", {"prompt": "summarize"})

    assert result.engine_used == "claude:mock"
    claude.run.assert_awaited_once()


# ── cost logging (AiUsageLog) ───────────────────────────────────────────────
async def test_cost_logged_for_confident_hosted_call(db_session):
    hosted = _hosted_returning(
        EngineResult(
            text="ok", engine_used="together:llama", confidence=0.9,
            cost_estimate_usd=0.0002, tokens_in=120, tokens_out=60,
        )
    )
    claude = _mock_claude()
    orch = _orch(hosted, claude)

    await orch.handle("skill_extraction", {"prompt": "x"}, {"db": db_session, "user_id": "u1"})

    rows = (await db_session.execute(select(AiUsageLog))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.engine_used == "together:llama"
    assert row.user_id == "u1"
    assert row.task_type == "skill_extraction"
    assert row.tokens_in == 120 and row.tokens_out == 60
    assert row.cost_estimate_usd == pytest.approx(0.0002)


async def test_cost_logged_for_hosted_then_claude_on_escalation(db_session):
    hosted = _hosted_returning(
        EngineResult(
            text="", engine_used="together:llama", confidence=None,
            cost_estimate_usd=0.00005, tokens_in=80, tokens_out=10,
        )
    )
    claude = _mock_claude(tokens_in=200, tokens_out=100, cost=0.01)
    orch = _orch(hosted, claude)

    await orch.handle("company_summary", {"prompt": "x"}, {"db": db_session, "user_id": "u2"})

    rows = (await db_session.execute(select(AiUsageLog))).scalars().all()
    engines = {r.engine_used for r in rows}
    # Both the billed (escalated) hosted call AND the Claude call are logged.
    assert engines == {"together:llama", "claude:mock"}
    assert len(rows) == 2


async def test_no_cost_log_without_session_does_not_error():
    # No context db and no usage_session_factory → logging is skipped silently.
    hosted = _hosted_returning(None)
    claude = _mock_claude()
    orch = _orch(hosted, claude)
    result = await orch.handle("company_summary", {"prompt": "x"})
    assert result.engine_used == "claude:mock"


# ── PII sanitizer ───────────────────────────────────────────────────────────
def test_sanitizer_strips_pii_keys_and_redacts_inline():
    payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "resume_text": "Reach me at jane@example.com or +1 415 555 1234. Skilled in RTOS/CAN.",
        "skills": ["CAN", "RTOS"],
    }
    clean = HostedModelEngine._sanitize_payload(payload)

    assert "full_name" not in clean and "email" not in clean  # identity keys dropped
    assert "jane@example.com" not in clean["resume_text"]
    assert "[REDACTED_EMAIL]" in clean["resume_text"]
    assert "[REDACTED_PHONE]" in clean["resume_text"]
    assert clean["skills"] == ["CAN", "RTOS"]  # non-PII content preserved


def test_sanitizer_redacts_nested_pii_keys():
    clean = HostedModelEngine._sanitize_payload({"candidate": {"name": "Bob", "years": 5}})
    assert clean["candidate"]["name"] == "[REDACTED_PII]"
    assert clean["candidate"]["years"] == 5


async def test_run_sanitizes_payload_before_sending(monkeypatch):
    engine = HostedModelEngine(api_key="test-key")
    captured = {}

    async def fake_chat(messages, model, max_tokens=None):
        captured["messages"] = messages
        return {"content": '{"ok": 1}', "tokens_in": 5, "tokens_out": 5, "finish_reason": "stop"}

    monkeypatch.setattr(engine, "_chat_completion", fake_chat)
    await engine.run("resume_parsing", {"email": "a@b.com", "prompt": "Contact a@b.com for details"})

    blob = json.dumps(captured["messages"])
    assert "a@b.com" not in blob
    assert "[REDACTED_EMAIL]" in blob


# ── confidence heuristic (v1) ───────────────────────────────────────────────
def _engine():
    return HostedModelEngine(api_key="test-key")


def test_json_confidence_valid_is_high():
    assert _engine()._score_confidence("skill_extraction", '{"skills": ["CAN"]}', "stop") >= 0.6


def test_json_confidence_fenced_is_high():
    fenced = "```json\n{\"skills\": [\"CAN\"]}\n```"
    assert _engine()._score_confidence("skill_extraction", fenced, "stop") >= 0.6


def test_json_confidence_invalid_escalates():
    assert _engine()._score_confidence("skill_extraction", "sorry, I cannot do that", "stop") < 0.6


def test_freeform_good_is_high():
    text = ("Acme Robotics is a mid-size embedded systems company building automotive "
            "ECUs and functional-safety tooling for tier-1 suppliers across Europe.")
    assert _engine()._score_confidence("company_summary", text, "stop") >= 0.6


def test_freeform_too_short_escalates():
    assert _engine()._score_confidence("company_summary", "Acme is good.", "stop") < 0.6


def test_freeform_repetition_loop_escalates():
    text = "buy " * 30
    assert _engine()._score_confidence("company_summary", text, "stop") < 0.6


def test_freeform_truncated_escalates():
    text = "word " * 40  # long enough, but finish_reason=length means truncated
    assert _engine()._score_confidence("company_summary", text.strip(), "length") < 0.6


def test_empty_output_is_zero_confidence():
    assert _engine()._score_confidence("company_summary", "", "stop") == 0.0


def test_cost_estimate_uses_together_pricing():
    # 1000 in + 1000 out at $0.00088/1k each.
    assert _engine()._estimate_cost(1000, 1000) == pytest.approx(0.00176)


# ── engine.run end-to-end (mocked provider) ─────────────────────────────────
async def test_run_accepts_valid_structured_output(monkeypatch):
    engine = HostedModelEngine(api_key="test-key")

    async def fake_chat(messages, model, max_tokens=None):
        return {"content": '{"skills": ["CAN", "RTOS"]}', "tokens_in": 50, "tokens_out": 20, "finish_reason": "stop"}

    monkeypatch.setattr(engine, "_chat_completion", fake_chat)
    result = await engine.run("skill_extraction", {"prompt": "extract"})

    assert result is not None
    assert result.confidence is not None and result.confidence >= 0.6
    # skill_extraction is routed to the Qwen model of the fleet.
    assert result.engine_used == f"together:{engine._model_for('skill_extraction')}"
    assert "Qwen" in result.engine_used
    assert result.tokens_in == 50 and result.tokens_out == 20
    assert result.cost_estimate_usd > 0


async def test_run_low_confidence_returns_confidence_none_but_bills(monkeypatch):
    engine = HostedModelEngine(api_key="test-key")

    async def fake_chat(messages, model, max_tokens=None):
        return {"content": "nope", "tokens_in": 10, "tokens_out": 5, "finish_reason": "stop"}

    monkeypatch.setattr(engine, "_chat_completion", fake_chat)
    result = await engine.run("skill_extraction", {"prompt": "x"})

    assert result.confidence is None  # → router escalates to Claude
    assert result.cost_estimate_usd > 0  # but the call is still billed


# ── open-model fleet + pluggable provider ───────────────────────────────────
async def test_fleet_routes_each_task_to_its_model(monkeypatch):
    engine = HostedModelEngine(api_key="test-key")
    seen: dict[str, str] = {}

    async def fake_chat(messages, model, max_tokens=None):
        seen["model"] = model
        return {"content": '{"ok": 1}', "tokens_in": 5, "tokens_out": 5, "finish_reason": "stop"}

    monkeypatch.setattr(engine, "_chat_completion", fake_chat)
    await engine.run("skill_extraction", {"prompt": "x"})
    assert "Qwen" in seen["model"]
    await engine.run("job_description_extraction", {"prompt": "x"})
    assert "Llama" in seen["model"]
    await engine.run("company_summary", {"prompt": "x" * 200})
    assert "gemma" in seen["model"].lower()


async def test_local_provider_needs_no_api_key(monkeypatch):
    # provider=local + no key → engine is usable (Ollama/vLLM need no key).
    engine = HostedModelEngine(provider="local", api_key=None, base_url="http://localhost:11434/v1")

    async def fake_chat(messages, model, max_tokens=None):
        return {"content": '{"skills": []}', "tokens_in": 5, "tokens_out": 5, "finish_reason": "stop"}

    monkeypatch.setattr(engine, "_chat_completion", fake_chat)
    result = await engine.run("skill_extraction", {"prompt": "x"})
    assert result is not None
    assert result.engine_used.startswith("local:")
    assert result.cost_estimate_usd == 0.0  # self-hosted → no vendor per-token cost


async def test_run_returns_none_when_unconfigured():
    assert await HostedModelEngine(api_key=None).run("skill_extraction", {"prompt": "x"}) is None
    assert await HostedModelEngine(api_key="k", enabled=False).run("skill_extraction", {"prompt": "x"}) is None


async def test_run_returns_none_for_non_allowed_task():
    engine = HostedModelEngine(api_key="k")
    assert await engine.run("resume_rewrite", {"prompt": "x"}) is None
    assert await engine.run("mentor_chat", {"prompt": "x"}) is None
