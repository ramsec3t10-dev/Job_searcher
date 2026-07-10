"""Unit tests — Adaptive Learning Service (Part A).

Covers the daily-mission skill-selection algorithm and the spaced-repetition
interval ladder. No LLM is invoked: skill selection is exercised directly (job
matching is deterministic), and spaced repetition is pure state maths.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register models
from app.database.base import Base
from app.models.career_twin import CareerTwin
from app.services.adaptive_learning_service import (
    SPACED_INTERVALS,
    AdaptiveLearningService,
)


def _utoday():
    return datetime.now(timezone.utc).date()


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


# ── Skill selection algorithm ────────────────────────────────────────────────

def test_focus_skill_prefers_in_demand_skill():
    twin = CareerTwin(
        user_id="u1",
        full_name="Ram",
        total_years_experience=4.0,
        current_role="Embedded Engineer",
        skills=[
            {"name": "autosar", "category": "automotive", "confidence": 0.3, "recency_score": 1.0},
            {"name": "cobol", "category": "programming", "confidence": 0.3, "recency_score": 1.0},
        ],
    )
    low = list(twin.skills)
    focus = AdaptiveLearningService(None)._select_focus_skill(twin, low)
    # AUTOSAR is required across many embedded jobs; COBOL by none.
    assert focus["name"] == "autosar"


def test_focus_skill_none_when_no_low_confidence():
    twin = CareerTwin(user_id="u1", skills=[{"name": "c", "confidence": 0.9}])
    assert AdaptiveLearningService(None)._select_focus_skill(twin, []) is None


def test_lower_confidence_breaks_demand_tie():
    twin = CareerTwin(
        user_id="u1",
        skills=[
            {"name": "cobol", "category": "programming", "confidence": 0.5, "recency_score": 1.0},
            {"name": "fortran", "category": "programming", "confidence": 0.2, "recency_score": 1.0},
        ],
    )
    focus = AdaptiveLearningService(None)._select_focus_skill(twin, list(twin.skills))
    # Neither skill is demanded by the embedded corpus (equal demand/salary=0),
    # so the weaker-confidence skill must win on the confidence term.
    assert focus["name"] == "fortran"


# ── Spaced repetition intervals ──────────────────────────────────────────────

async def test_spaced_repetition_advances_on_confidence(db):
    svc = AdaptiveLearningService(db)
    s1 = await svc.update_spaced_repetition("u1", "can", was_confident=True)
    assert s1["interval_index"] == 1
    assert s1["consecutive_confident"] == 1
    assert s1["next_review_date"] == (_utoday() + timedelta(days=SPACED_INTERVALS[1])).isoformat()

    s2 = await svc.update_spaced_repetition("u1", "can", was_confident=True)
    assert s2["interval_index"] == 2
    assert s2["consecutive_confident"] == 2


async def test_spaced_repetition_resets_on_failure(db):
    svc = AdaptiveLearningService(db)
    await svc.update_spaced_repetition("u1", "can", was_confident=True)
    await svc.update_spaced_repetition("u1", "can", was_confident=True)
    s = await svc.update_spaced_repetition("u1", "can", was_confident=False)
    assert s["interval_index"] == 0
    assert s["consecutive_confident"] == 0
    assert s["next_review_date"] == (_utoday() + timedelta(days=SPACED_INTERVALS[0])).isoformat()


async def test_spaced_repetition_caps_at_last_interval(db):
    svc = AdaptiveLearningService(db)
    for _ in range(len(SPACED_INTERVALS) + 3):
        s = await svc.update_spaced_repetition("u1", "can", was_confident=True)
    assert s["interval_index"] == len(SPACED_INTERVALS) - 1


async def test_review_queue_orders_by_overdue(db):
    svc = AdaptiveLearningService(db)
    await svc.memory_repo.store(
        "u1", "spaced_repetition", "can due",
        full_content=json.dumps({
            "skill": "can",
            "next_review_date": (_utoday() - timedelta(days=5)).isoformat(),
        }),
        tags=["can"],
    )
    await svc.memory_repo.store(
        "u1", "spaced_repetition", "spi due",
        full_content=json.dumps({
            "skill": "spi",
            "next_review_date": (_utoday() - timedelta(days=1)).isoformat(),
        }),
        tags=["spi"],
    )
    await svc.memory_repo.store(
        "u1", "spaced_repetition", "future",
        full_content=json.dumps({
            "skill": "i2c",
            "next_review_date": (_utoday() + timedelta(days=3)).isoformat(),
        }),
        tags=["i2c"],
    )
    queue = await svc.get_review_queue("u1")
    assert queue == ["can", "spi"]  # most overdue first, future excluded
