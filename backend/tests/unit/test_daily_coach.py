"""Unit tests for Module 11 — daily coach."""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.models.career_twin import CareerTwin
from app.models.daily_checkin import DailyCheckin
from app.services.daily_coach_service import DailyCoachService

import app.models  # noqa: F401


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _twin(db, user_id="u1", skills=None, readiness=60):
    twin = CareerTwin(user_id=user_id, full_name="Ram", email="", phone="", location="",
                      skills=skills or [], known_weaknesses=[], strengths=[],
                      interview_readiness_score=readiness, profile_completeness=70,
                      market_value_score=65, embedded_domain_score=80,
                      career_level="mid", change_log={})
    db.add(twin)
    await db.flush()
    return twin


@pytest.mark.asyncio
async def test_onboarding_brief_without_twin(db):
    brief = await DailyCoachService(db).get_daily_brief("nouser")
    assert brief["onboarding"] is True
    assert "focus_today" in brief
    assert brief["streak_days"] == 0


@pytest.mark.asyncio
async def test_brief_with_twin_has_snapshot_and_focus(db):
    await _twin(db, skills=[{"name": "c", "confidence": 0.9},
                            {"name": "autosar", "confidence": 0.3},
                            {"name": "can", "confidence": 0.2}])
    brief = await DailyCoachService(db).get_daily_brief("u1")
    assert brief["onboarding"] is False
    assert brief["career_snapshot"]["interview_readiness_score"] == 60
    # weakest-confidence skills surface as today's focus
    joined = " ".join(brief["focus_today"]).lower()
    assert "can" in joined or "autosar" in joined


@pytest.mark.asyncio
async def test_checkin_creates_and_is_idempotent_per_day(db):
    svc = DailyCoachService(db)
    r1 = await svc.check_in("u1", tasks_completed=2)
    r2 = await svc.check_in("u1", tasks_completed=1)  # same day, keeps max
    assert r1["streak_days"] == 1
    assert r2["streak_days"] == 1
    assert r2["tasks_completed"] == 2


@pytest.mark.asyncio
async def test_streak_counts_consecutive_days(db):
    today = datetime.now(timezone.utc).date()
    for i in range(3):  # today, yesterday, day before
        d = (today - timedelta(days=i)).isoformat()
        db.add(DailyCheckin(user_id="u1", checkin_date=d, tasks_completed=1))
    await db.flush()
    streak = await DailyCoachService(db)._streak("u1")
    assert streak == 3


@pytest.mark.asyncio
async def test_streak_breaks_on_gap(db):
    today = datetime.now(timezone.utc).date()
    for i in (0, 1, 3):  # gap at day 2
        d = (today - timedelta(days=i)).isoformat()
        db.add(DailyCheckin(user_id="u1", checkin_date=d, tasks_completed=1))
    await db.flush()
    streak = await DailyCoachService(db)._streak("u1")
    assert streak == 2  # today + yesterday only


@pytest.mark.asyncio
async def test_brief_includes_streak_after_checkin(db):
    await _twin(db)
    svc = DailyCoachService(db)
    await svc.check_in("u1", tasks_completed=1)
    brief = await svc.get_daily_brief("u1")
    assert brief["streak_days"] == 1
    assert brief["motivation"]
