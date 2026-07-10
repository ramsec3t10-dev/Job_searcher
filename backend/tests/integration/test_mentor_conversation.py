"""EMBEDHUNT AI — mentor conversation integration test.

Starts a conversation, runs multiple turns, and verifies the conversation
history is persisted (ai_conversations) and long-term memory is written. Bedrock
is mocked via the agent's ``router.route``.
"""
import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM tables
from app.agents.mentor_agent import MentorAgent
from app.database.base import Base
from app.llm.conversation_manager import Conversation
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


def _mock_advice(agent, advice: str) -> AsyncMock:
    payload = {"advice": advice, "action_items": ["step 1"], "priority": "high"}
    response = AIResponse(
        content=json.dumps(payload), model_used="claude-sonnet-4-6",
        input_tokens=10, output_tokens=20, cost_usd=0.0002,
        latency_ms=5.0, cached=False, task_type=TaskType.MENTORING,
    )
    mock = AsyncMock(return_value=response)
    agent.router.route = mock
    return mock


async def _count(db, model, **filters) -> int:
    stmt = select(func.count()).select_from(model)
    for col, val in filters.items():
        stmt = stmt.where(getattr(model, col) == val)
    return (await db.execute(stmt)).scalar_one()


@pytest.mark.asyncio
async def test_mentor_multi_turn_conversation(db):
    user_id = "user-mentor"
    conversation_id = "conv-1"
    await CareerTwinService(db).get_or_create(user_id)
    await db.flush()

    agent = MentorAgent(db)

    _mock_advice(agent, "Focus on RTOS fundamentals.")
    r1 = await agent.advise(user_id, "How do I get into Qualcomm?", conversation_id)
    assert r1.advice

    _mock_advice(agent, "Next, practice CAN driver debugging.")
    r2 = await agent.advise(user_id, "What after RTOS?", conversation_id)
    assert r2.advice

    # History: 2 user + 2 assistant messages persisted for this conversation.
    turns = await _count(db, Conversation, user_id=user_id, conversation_id=conversation_id)
    assert turns >= 4

    # Long-term memory updated by the agent on each turn.
    memories = await _count(db, MemoryEntry, user_id=user_id)
    assert memories >= 2
