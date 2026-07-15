"""EMBEDHUNT AI — /admin/ai-usage endpoint + AiUsageRepository aggregation."""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.database.session as db_session
import app.models  # noqa: F401
from app.auth.jwt import create_access_token
from app.database.base import Base
from app.main import app
from app.models.orchestrator_usage import AiUsageLog
from app.repositories.ai_usage_repository import AiUsageRepository


def _row(tier, engine_used, task, cost, **kw):
    return AiUsageLog(user_id="u1", task_type=task, engine_used=engine_used, engine_tier=tier,
                      cost_estimate_usd=cost, latency_ms=kw.get("latency", 10.0),
                      tokens_in=kw.get("ti", 0), tokens_out=kw.get("to", 0))


# A realistic month of routing: mostly free tiers, a slice of hosted, a sliver of Claude.
def _seed_rows():
    rows = []
    rows += [_row("rule", "rule:daily_brief", "daily_brief", 0.0) for _ in range(40)]
    rows += [_row("kg", "knowledge_graph", "skill_query", 0.0) for _ in range(20)]
    rows += [_row("cache", "together:qwen", "skill_extraction", 0.0) for _ in range(25)]
    rows += [_row("hosted", "together:Qwen/Qwen2.5-72B-Instruct-Turbo", "skill_extraction", 0.0002, ti=120, to=60) for _ in range(10)]
    rows += [_row("hosted", "together:google/gemma-2-27b-it", "company_summary", 0.00015, ti=90, to=40) for _ in range(3)]
    rows += [_row("claude", "claude:claude-sonnet-4-6", "mentor_chat", 0.011, ti=200, to=100) for _ in range(4)]
    rows += [_row("claude", "claude:claude-sonnet-4-6", "resume_rewrite", 0.02, ti=300, to=200) for _ in range(1)]
    return rows  # 103 requests total


@pytest_asyncio.fixture
async def seeded_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        s.add_all(_seed_rows())
        await s.commit()
    yield engine, maker
    await engine.dispose()


# ── repository aggregation ──────────────────────────────────────────────────
async def test_monthly_summary_aggregates(seeded_engine):
    engine, maker = seeded_engine
    async with maker() as s:
        summary = await AiUsageRepository(s).monthly_summary()

    assert summary["total_requests"] == 103
    # Cost = hosted (10*0.0002 + 3*0.00015) + claude (4*0.011 + 0.02)
    assert summary["total_cost_usd"] == pytest.approx(0.002 + 0.00045 + 0.044 + 0.02, abs=1e-6)
    by = summary["by_engine"]
    assert by["rule"]["requests"] == 40 and by["rule"]["cost_usd"] == 0.0
    assert by["cache"]["requests"] == 25 and by["cache"]["cost_usd"] == 0.0
    assert by["claude"]["requests"] == 5
    # The launch KPI: Claude share ~4.85% (5/103) — under the 5% target.
    assert summary["claude_pct_requests"] == pytest.approx(round(100 * 5 / 103, 2))
    assert summary["claude_pct_requests"] < 5.0
    # Top task types by cost: mentor_chat + resume_rewrite (Claude) lead.
    top_tasks = [t["task_type"] for t in summary["top_task_types"]]
    assert "mentor_chat" in top_tasks and "resume_rewrite" in top_tasks
    assert len(summary["top_task_types"]) <= 10


async def test_month_boundary_excludes_old_rows(seeded_engine):
    engine, maker = seeded_engine
    async with maker() as s:
        # An old row (last month) must not count toward this month's totals.
        old = _row("claude", "claude:mock", "mentor_chat", 5.0)
        s.add(old)
        await s.flush()
        old.created_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        await s.commit()
        summary = await AiUsageRepository(s).monthly_summary()
    assert summary["total_cost_usd"] < 1.0  # the $5 old row is excluded


# ── endpoint auth ───────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(seeded_engine):
    engine, maker = seeded_engine

    async def _override_db():
        async with maker() as s:
            yield s

    app.dependency_overrides[db_session.get_db] = _override_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_ai_usage_requires_admin(client):
    r = await client.get("/api/v1/admin/ai-usage",
                         headers={"Authorization": f"Bearer {create_access_token('u1', 'candidate')}"})
    assert r.status_code == 403


async def test_ai_usage_admin_ok(client):
    r = await client.get("/api/v1/admin/ai-usage",
                         headers={"Authorization": f"Bearer {create_access_token('admin1', 'platform_admin')}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_requests"] == 103
    assert set(body["by_engine"]) >= {"rule", "kg", "cache", "hosted", "claude"}
    assert "claude_pct_requests" in body
