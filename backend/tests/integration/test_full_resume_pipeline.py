"""EMBEDHUNT AI — full resume pipeline integration test.

Exercises: parse resume → create Career Twin → score vs a job → gap analysis,
end to end against an in-memory SQLite DB. Bedrock is never touched — each
agent's ``router.route`` is mocked to return staged payloads. Asserts the DB
records (twin, memory entries) are created along the way.
"""
import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM tables
from app.agents.matching_agent import MatchingAgent
from app.agents.resume_agent import ResumeAgent
from app.database.base import Base
from app.llm.conversation_manager import Conversation  # noqa: F401
from app.llm.cost_tracker import AIUsageLog  # noqa: F401
from app.llm.model_selector import TaskType
from app.llm.router import AIResponse
from app.models.memory import MemoryEntry
from app.services.career_twin_service import CareerTwinService


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


def _mock_route(agent, payload: dict) -> AsyncMock:
    response = AIResponse(
        content=json.dumps(payload), model_used="claude-sonnet-4-6",
        input_tokens=10, output_tokens=20, cost_usd=0.0001,
        latency_ms=5.0, cached=False, task_type=TaskType.EXTRACTION,
    )
    mock = AsyncMock(return_value=response)
    agent.router.route = mock
    return mock


async def _memory_count(db, user_id: str) -> int:
    stmt = select(func.count()).select_from(MemoryEntry).where(MemoryEntry.user_id == user_id)
    return (await db.execute(stmt)).scalar_one()


@pytest.mark.asyncio
async def test_full_resume_pipeline(db):
    user_id = "user-pipeline"

    # 1. Parse resume.
    resume_agent = ResumeAgent(db)
    _mock_route(resume_agent, {
        "skills": ["c", "freertos", "can"], "total_years": 6,
        "contact": {"name": "Ram", "email": "ram@example.com"},
        "summary": "Embedded engineer",
    })
    parsed = await resume_agent.parse("6 years embedded C, FreeRTOS, CAN", user_id)
    assert "c" in parsed.skills

    # 2. Create the Career Twin (persisted).
    twin = await CareerTwinService(db).get_or_create(user_id)
    await db.flush()
    assert twin is not None
    assert twin.user_id == user_id

    # 3. Score resume against a job.
    _mock_route(resume_agent, {
        "score": 78, "ats_score": 70, "missing_keywords": ["autosar"],
        "strengths": ["rtos"], "improvements": ["add metrics"],
    })
    score = await resume_agent.score("resume text", "AUTOSAR firmware role", user_id)
    assert score.score == 78

    # 4. Gap analysis.
    matching_agent = MatchingAgent(db)
    _mock_route(matching_agent, {
        "critical_gaps": ["autosar"], "estimated_upskill_weeks": 8,
        "learning_priority": ["autosar"], "immediate_focus": "autosar",
        "gap_summary": "Learn AUTOSAR",
    })
    job = {"title": "AUTOSAR Engineer", "description": "AUTOSAR, CAN, ISO 26262",
           "required_skills": ["autosar", "can"]}
    gaps = await matching_agent.analyze_gaps(twin, job, user_id)
    assert "autosar" in gaps.critical_gaps

    # DB assertions: twin persisted and memory entries were written by the agents.
    reloaded = await CareerTwinService(db).get_or_create(user_id)
    assert reloaded.user_id == user_id
    assert await _memory_count(db, user_id) >= 1
