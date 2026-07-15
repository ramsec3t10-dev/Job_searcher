"""EMBEDHUNT AI — Gateway + real-call-site adoption tests.

Proves the app actually *runs on* the architecture: the OrchestratorGateway
grounds a task in the knowledge stack and routes it through the real
Orchestrator chain, and two migrated services (MentorService → Claude tier,
CompanyIntelligenceService.summarize → open-model tier) go through it. The
terminal engines are mocked (no Bedrock / Together); DB is in-memory SQLite.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.career_twin import CareerTwin
from app.orchestrator import Orchestrator, OrchestratorGateway
from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.hosted_model_engine import HostedModelEngine
from app.orchestrator.rule_engine import RuleEngine
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


def _twin(user_id):
    return CareerTwin(
        user_id=user_id, current_role="Firmware Engineer", current_company="Bosch",
        career_level="mid", skills=[{"name": "CAN", "confidence": 0.9}],
        career_goals={"target_role": "AUTOSAR Engineer"}, market_value_score=64,
    )


def _mock_claude(text="claude reply"):
    m = MagicMock(spec=ClaudeEngine)
    m.run = AsyncMock(return_value=EngineResult(
        text=text, engine_used="claude:claude-sonnet-4-6", cost_estimate_usd=0.01,
        tokens_in=100, tokens_out=50))
    return m


def _mock_open(text='{"ok": 1}', confidence=0.9):
    m = MagicMock(spec=HostedModelEngine)
    m.run = AsyncMock(return_value=EngineResult(
        text=text, engine_used="together:Qwen/Qwen2.5-72B-Instruct-Turbo",
        confidence=confidence, cost_estimate_usd=0.0002, tokens_in=120, tokens_out=60))
    return m


def _gateway(claude=None, open_model=None):
    orch = Orchestrator(
        rule_engine=RuleEngine(),
        knowledge_graph_engine=KnowledgeGraphEngine(),
        cache_engine=CacheEngine(force_memory=True),
        hosted_model_engine=open_model or _mock_open(),
        claude_engine=claude or _mock_claude(),
    )
    return OrchestratorGateway(orchestrator=orch)


# ── gateway grounds + routes ────────────────────────────────────────────────
async def test_gateway_grounds_task_with_knowledge(session):
    session.add(_twin("u1"))
    await session.flush()
    claude = _mock_claude()
    gw = _gateway(claude=claude)

    await gw.run("mentor_chat", {"prompt": "How do I get promoted?"}, user_id="u1", session=session)

    # Claude was invoked with a grounded system preamble derived from the twin.
    ctx = claude.run.await_args.args[2]
    assert "AUTOSAR Engineer" in ctx["system"]      # from the user's goals layer
    assert ctx["user_id"] == "u1"


async def test_gateway_open_model_task_short_circuits_before_claude(session):
    claude = _mock_claude()
    gw = _gateway(claude=claude, open_model=_mock_open(text="Acme builds embedded ECUs for automotive."))

    result = await gw.run("company_summary", {"prompt": "Summarize Acme"}, user_id="u1", session=session)

    assert result.engine_used.startswith("together:")
    claude.run.assert_not_awaited()  # confident open-model answer → no Claude


# ── MentorService adoption (Claude tier) ────────────────────────────────────
async def test_mentor_service_routes_through_orchestrator(session):
    from app.services.mentor_service import MentorService

    session.add(_twin("u1"))
    await session.flush()
    svc = MentorService(session, gateway=_gateway(claude=_mock_claude("Focus on AUTOSAR + ISO 26262.")))

    out = await svc.chat("u1", "What should I learn next?")
    assert out["reply"] == "Focus on AUTOSAR + ISO 26262."
    assert out["source"].startswith("claude:")


async def test_mentor_service_falls_back_when_orchestrator_empty(session):
    from app.services.mentor_service import MentorService

    session.add(_twin("u1"))
    await session.flush()
    # Claude returns empty → service must fall back to the deterministic advisor.
    svc = MentorService(session, gateway=_gateway(claude=_mock_claude(text="")))

    out = await svc.chat("u1", "How should I prepare for interviews?")
    assert out["source"] == "rule_based"
    assert out["reply"]  # non-empty deterministic guidance


# ── CompanyIntelligenceService adoption (open-model tier) ────────────────────
async def test_company_summarize_uses_open_model_tier(session):
    from app.services.company_intel_service import CompanyIntelligenceService

    svc = CompanyIntelligenceService(
        session, gateway=_gateway(open_model=_mock_open(text="Bosch is a tier-1 automotive supplier.")))
    # Pick a real profile name from the company DB.
    from app.company.profiles import all_profiles

    name = all_profiles()[0].name
    out = await svc.summarize(name)
    assert out["found"] is True
    assert out["summary"] == "Bosch is a tier-1 automotive supplier."
    assert out["engine_used"].startswith("together:")


async def test_company_summarize_unknown_company(session):
    from app.services.company_intel_service import CompanyIntelligenceService

    svc = CompanyIntelligenceService(session, gateway=_gateway())
    out = await svc.summarize("Nonexistent Corp XYZ")
    assert out["found"] is False
