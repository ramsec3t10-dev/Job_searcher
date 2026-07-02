"""Unit tests for Module 9 — adaptive roadmap."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.adaptive_roadmap import AdaptiveRoadmap, AdaptiveRoadmapEngine, get_adaptive_engine
from app.database.base import Base
from app.models.career_twin import CareerTwin
from app.services.adaptive_roadmap_service import AdaptiveRoadmapService

import app.models  # noqa: F401


# ── pure engine ──────────────────────────────────────────────────────────────

def test_confident_skills_excluded():
    eng = AdaptiveRoadmapEngine()
    rm = eng.build(skill_confidence={"c": 0.9, "can": 0.8},
                   target_skills=["c", "can", "autosar"],
                   current_score=60, job_title="Auto")
    names = {t.skill for t in rm.tasks}
    assert "autosar" in names
    assert "c" not in names and "can" not in names


def test_reinforcement_vs_gap_classification():
    eng = AdaptiveRoadmapEngine()
    rm = eng.build(skill_confidence={"autosar": 0.3},
                   target_skills=["autosar", "freertos"],
                   current_score=50, job_title="Auto")
    by = {t.skill: t for t in rm.tasks}
    assert by["autosar"].kind == "reinforcement"
    assert by["freertos"].kind == "gap"
    # reinforcement needs fewer hours than the full skill estimate
    assert by["autosar"].estimated_hours < 80


def test_demand_drives_priority():
    eng = AdaptiveRoadmapEngine()
    rm = eng.build(skill_confidence={},
                   target_skills=["freertos", "can"],
                   current_score=40, job_title="X",
                   demand={"can": 5, "freertos": 1})
    # higher demand skill should be prioritised first
    assert rm.tasks[0].skill == "can"
    assert rm.tasks[0].priority == 1


def test_weekly_scheduling_and_milestones():
    eng = AdaptiveRoadmapEngine()
    rm = eng.build(skill_confidence={},
                   target_skills=["c", "c++", "autosar", "linux kernel"],
                   current_score=30, job_title="X", hours_per_week=20)
    assert rm.total_weeks >= 1
    assert rm.tasks[-1].week == rm.total_weeks
    assert rm.milestones
    assert rm.milestones[-1]["projected_score"] == rm.projected_score


def test_projected_score_increases():
    eng = AdaptiveRoadmapEngine()
    rm = eng.build(skill_confidence={}, target_skills=["c", "can", "spi"],
                   current_score=50, job_title="X")
    assert rm.projected_score > 50
    assert rm.projected_score <= 99


def test_no_gaps_returns_empty_plan():
    eng = AdaptiveRoadmapEngine()
    rm = eng.build(skill_confidence={"c": 0.9}, target_skills=["c"],
                   current_score=80, job_title="X")
    assert rm.tasks == []
    assert "No gaps" in rm.summary


def test_singleton_accessor():
    assert get_adaptive_engine() is get_adaptive_engine()


# ── service (twin-driven) ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _make_twin(db, user_id="u1", skills=None, dream=None):
    twin = CareerTwin(user_id=user_id, full_name="Ram", email="", phone="", location="",
                      skills=skills or [], dream_companies=dream or [])
    db.add(twin)
    await db.flush()
    return twin


@pytest.mark.asyncio
async def test_service_targets_uses_twin_confidence(db):
    await _make_twin(db, skills=[{"name": "c", "confidence": 0.9},
                                 {"name": "can", "confidence": 0.2}])
    out = await AdaptiveRoadmapService(db).roadmap_for_targets(
        "u1", target_skills=["c", "can", "autosar"], job_title="Auto")
    skills = {t["skill"] for t in out["tasks"]}
    assert "c" not in skills           # confident → excluded
    assert "can" in skills and "autosar" in skills
    assert out["current_score"] == 33  # 1 of 3 confident


@pytest.mark.asyncio
async def test_service_requires_twin(db):
    with pytest.raises(Exception):
        await AdaptiveRoadmapService(db).roadmap_for_targets("nouser", ["c"])


@pytest.mark.asyncio
async def test_service_dream_companies(db):
    await _make_twin(db, skills=[{"name": "c", "confidence": 0.9}],
                     dream=["Bosch", "NVIDIA"])
    out = await AdaptiveRoadmapService(db).roadmap_for_dream_companies("u1")
    assert out["dream_companies"] == ["Bosch", "NVIDIA"]
    assert out["tasks"]  # there are gaps toward dream stacks
