"""EMBEDHUNT AI — Phase 5 training-capture + eval tests.

In-memory SQLite; no network. Covers: consent + settings gating, PII scrubbing,
served + shadow capture through the real Orchestrator, cost-log telemetry
(escalated/confidence), feedback labeling, dataset export filters, and the eval
harness (structured + freeform + shadow-capture scoring).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.config.settings import settings
from app.database.base import Base
from app.models.ai_interaction import AiInteraction
from app.models.orchestrator_usage import AiUsageLog
from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.hosted_model_engine import HostedModelEngine
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine
from app.orchestrator.router import Orchestrator
from app.orchestrator.rule_engine import RuleEngine
from app.training import TrainingCapture, record_feedback
from app.training.capture import _prompt_text
from app.training.dataset import export_task, dataset_stats
from app.training import eval as ev


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def capture_on():
    orig = settings.ORCHESTRATOR_CAPTURE_TRAINING_DATA
    settings.ORCHESTRATOR_CAPTURE_TRAINING_DATA = True
    yield
    settings.ORCHESTRATOR_CAPTURE_TRAINING_DATA = orig


def _kg_none():
    kg = MagicMock(spec=KnowledgeGraphEngine)
    kg.run = AsyncMock(return_value=None)
    return kg


def _claude(text='{"skills": ["CAN"]}'):
    c = MagicMock(spec=ClaudeEngine)
    c.run = AsyncMock(return_value=EngineResult(
        text=text, engine_used="claude:claude-sonnet-4-6", cost_estimate_usd=0.01,
        tokens_in=200, tokens_out=100))
    return c


def _hosted(text='{"skills": ["CAN"]}', confidence=0.95):
    h = MagicMock(spec=HostedModelEngine)
    h.run = AsyncMock(return_value=EngineResult(
        text=text, engine_used="together:Qwen/Qwen2.5-72B-Instruct-Turbo", confidence=confidence,
        cost_estimate_usd=0.0002, tokens_in=120, tokens_out=60))
    return h


def _orch(capture=None, claude=None, hosted=None):
    return Orchestrator(
        rule_engine=RuleEngine(), knowledge_graph_engine=_kg_none(),
        cache_engine=CacheEngine(force_memory=True),
        hosted_model_engine=hosted or _hosted(), claude_engine=claude or _claude(),
        capture=capture,
    )


# ── consent + settings gating ───────────────────────────────────────────────
async def test_no_capture_when_flag_off(session):
    # capture flag OFF (default) → nothing written even with consent + capture obj.
    orch = _orch(capture=TrainingCapture())
    await orch.handle("skill_extraction", {"prompt": "x"}, {"db": session, "user_id": "u1", "consent": True})
    rows = (await session.execute(select(AiInteraction))).scalars().all()
    assert rows == []


async def test_no_capture_without_consent(session, capture_on):
    orch = _orch(capture=TrainingCapture())
    # consent missing → governance blocks capture even though the flag is on.
    await orch.handle("skill_extraction", {"prompt": "x"}, {"db": session, "user_id": "u1"})
    rows = (await session.execute(select(AiInteraction))).scalars().all()
    assert rows == []


async def test_captures_served_with_consent(session, capture_on):
    orch = _orch(capture=TrainingCapture(), hosted=_hosted(text='{"skills": ["CAN", "RTOS"]}'))
    await orch.handle("skill_extraction", {"prompt": "extract", "system": "You extract skills."},
                      {"db": session, "user_id": "u1", "consent": True})
    rows = (await session.execute(select(AiInteraction))).scalars().all()
    assert len(rows) == 1
    r = rows[0]
    assert r.role == "served"
    assert r.task_type == "skill_extraction"
    assert r.engine_used.startswith("together:")
    assert r.consented is True
    assert '"skills"' in r.output


# ── PII scrubbing ───────────────────────────────────────────────────────────
async def test_pii_scrubbed_before_storage(session, capture_on):
    orch = _orch(capture=TrainingCapture(),
                 hosted=_hosted(text="Reach the candidate at jane@example.com or +1 415 555 1234."))
    # company_summary is freeform (open-model), so the low bar returns confidence; force accept
    await orch.handle("company_summary",
                      {"prompt": "Summarize. Contact me at bob@corp.com", "system": "sys"},
                      {"db": session, "user_id": "u1", "consent": True})
    r = (await session.execute(select(AiInteraction))).scalars().first()
    assert r is not None
    assert "bob@corp.com" not in r.prompt and "[REDACTED_EMAIL]" in r.prompt
    assert "jane@example.com" not in r.output and "[REDACTED_EMAIL]" in r.output
    assert r.pii_scrubbed is True


# ── shadow capture ──────────────────────────────────────────────────────────
async def test_shadow_candidate_captured(session, capture_on, monkeypatch):
    monkeypatch.setattr(settings, "ORCHESTRATOR_SHADOW_MODEL_ENABLED", True)
    shadow_engine = MagicMock()
    shadow_engine.generate = AsyncMock(return_value=EngineResult(
        text='{"skills": ["CAN"]}', engine_used="shadow:embedhunt-distill-v0",
        confidence=0.8, cost_estimate_usd=0.0, tokens_in=100, tokens_out=40))
    orch = _orch(capture=TrainingCapture(shadow_engine=shadow_engine))

    await orch.handle("skill_extraction", {"prompt": "extract"},
                      {"db": session, "user_id": "u1", "consent": True})

    rows = (await session.execute(select(AiInteraction).order_by(AiInteraction.role))).scalars().all()
    roles = {r.role for r in rows}
    assert roles == {"served", "shadow_candidate"}
    shadow = next(r for r in rows if r.role == "shadow_candidate")
    served = next(r for r in rows if r.role == "served")
    assert shadow.parent_id == served.id
    assert shadow.engine_used.startswith("shadow:")
    shadow_engine.generate.assert_awaited_once()  # candidate ran, but was never served


# ── cost-log telemetry (escalated + confidence) ─────────────────────────────
async def test_usage_log_records_escalation_and_confidence(session):
    # hosted low confidence → escalates to Claude; the served (Claude) row is escalated.
    hosted = _hosted(text="nope", confidence=None)
    orch = _orch(hosted=hosted, claude=_claude())
    await orch.handle("company_summary", {"prompt": "x"}, {"db": session, "user_id": "u1"})
    rows = (await session.execute(select(AiUsageLog).order_by(AiUsageLog.engine_used))).scalars().all()
    claude_row = next(r for r in rows if r.engine_used.startswith("claude:"))
    assert claude_row.escalated is True  # cheap tier failed → hard-example signal


# ── feedback labeling ───────────────────────────────────────────────────────
async def test_record_feedback_labels_interaction(session, capture_on):
    orch = _orch(capture=TrainingCapture())
    await orch.handle("skill_extraction", {"prompt": "x"}, {"db": session, "user_id": "u1", "consent": True})
    row = (await session.execute(select(AiInteraction))).scalars().first()

    updated = await record_feedback(session, row.id, accepted=True, rating=5, outcome="interview")
    assert updated.accepted is True
    assert updated.rating == 5
    assert updated.outcome == "interview"


# ── dataset export ──────────────────────────────────────────────────────────
async def test_dataset_export_filters(session):
    # Seed rows directly.
    session.add_all([
        AiInteraction(user_id="u1", task_type="skill_extraction", engine_used="claude:sonnet",
                      role="served", system="sys", prompt="p1", output='{"a":1}', consented=True, accepted=True),
        AiInteraction(user_id="u1", task_type="skill_extraction", engine_used="together:qwen",
                      role="served", prompt="p2", output='{"a":2}', consented=True, accepted=False),
        AiInteraction(user_id="u1", task_type="skill_extraction", engine_used="together:qwen",
                      role="served", prompt="p3", output='{"a":3}', consented=False),
    ])
    await session.flush()

    all_ok = await export_task(session, "skill_extraction")  # consented + not-rejected
    assert len(all_ok) == 1  # p1 (p2 rejected, p3 not consented)
    assert all_ok[0]["messages"][0]["role"] == "system"
    assert all_ok[0]["completion"] == '{"a":1}'

    teacher = await export_task(session, "skill_extraction", teacher_only=True)
    assert len(teacher) == 1 and teacher[0]["meta"]["engine"].startswith("claude:")

    stats = await dataset_stats(session, "skill_extraction")
    assert stats["served"] == 3


# ── eval harness ────────────────────────────────────────────────────────────
def test_prompt_text_extraction():
    assert _prompt_text({"prompt": "hello"}) == "hello"
    assert _prompt_text({"messages": [{"role": "user", "content": "hi"}]}) == "hi"


def test_structured_score_exact_and_partial():
    assert ev.score_example("skill_extraction", '{"skills": ["CAN"]}', '{"skills": ["CAN"]}') == 1.0
    assert ev.score_example("skill_extraction", '{"skills": ["CAN"]}', "not json") == 0.0
    partial = ev.score_example("skill_extraction", '{"a": 1, "b": 2}', '{"a": 1, "b": 99}')
    assert 0.0 < partial < 1.0


def test_freeform_score():
    assert ev.score_example("company_summary", "acme builds ecus", "acme builds ecus") == 1.0
    assert ev.score_example("company_summary", "acme builds ecus", "totally different text") < 0.5


def test_evaluate_report_and_promotable():
    pairs = [('{"a":1}', '{"a":1}'), ('{"a":2}', '{"a":2}'), ('{"a":3}', '{"a":3}')]
    report = ev.evaluate("skill_extraction", pairs, threshold=0.7)
    assert report.n == 3 and report.mean_score == 1.0 and report.pass_rate == 1.0
    assert report.promotable() is True


async def test_evaluate_shadow_capture(session):
    served = AiInteraction(user_id="u1", task_type="skill_extraction", engine_used="claude:sonnet",
                           role="served", prompt="p", output='{"skills": ["CAN", "RTOS"]}', consented=True)
    session.add(served)
    await session.flush()
    session.add(AiInteraction(user_id="u1", task_type="skill_extraction", engine_used="shadow:v0",
                              role="shadow_candidate", parent_id=served.id,
                              prompt="p", output='{"skills": ["CAN", "RTOS"]}', consented=True))
    await session.flush()

    report = await ev.evaluate_shadow_capture(session, "skill_extraction")
    assert report.n == 1
    assert report.mean_score == 1.0  # candidate matched the served reference exactly
