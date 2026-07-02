"""Unit tests for Module 6 — feedback loop."""
from dataclasses import dataclass, field

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.models.career_twin import CareerTwin
from app.services.feedback_service import FeedbackService

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


@dataclass
class _Match:
    company: str
    total_score: int
    matched_skills: list = field(default_factory=list)
    rank: int = 0


@pytest.mark.asyncio
async def test_record_feedback_persists(db):
    svc = FeedbackService(db)
    out = await svc.record_feedback("u1", "interview", job_id="j1", company="Bosch",
                                    skills="c,freertos,can", match_score=82)
    assert out["signal"] == 0.8
    assert out["job_id"] == "j1"


@pytest.mark.asyncio
async def test_unknown_type_rejected(db):
    with pytest.raises(ValueError):
        await FeedbackService(db).record_feedback("u1", "nonsense")


@pytest.mark.asyncio
async def test_affinities_positive_and_negative(db):
    svc = FeedbackService(db)
    await svc.record_feedback("u1", "offer", company="NVIDIA", skills="c++,linux kernel")
    await svc.record_feedback("u1", "dismissed", company="WebCo", skills="react,css")
    aff = await svc.get_affinities("u1")
    assert aff["skill_affinity"]["c++"] > 0
    assert aff["skill_affinity"]["react"] < 0
    assert aff["company_affinity"]["nvidia"] > 0


@pytest.mark.asyncio
async def test_summary_buckets(db):
    svc = FeedbackService(db)
    await svc.record_feedback("u1", "saved", skills="can")
    await svc.record_feedback("u1", "rejected", skills="verilog")
    summary = await svc.get_feedback_summary("u1")
    assert summary["total_events"] == 2
    assert "can" in summary["preferred_skills"]
    assert "verilog" in summary["aversive_skills"]


@pytest.mark.asyncio
async def test_strong_positive_updates_twin_strengths(db):
    twin = CareerTwin(user_id="u1", full_name="Ram", email="", phone="", location="",
                      skills=[{"name": "can", "confidence": 0.6}], strengths=[])
    db.add(twin)
    await db.flush()
    await FeedbackService(db).record_feedback("u1", "offer", company="Bosch", skills="can,spi")
    await db.refresh(twin)
    assert "can" in (twin.strengths or [])


@pytest.mark.asyncio
async def test_rejection_lowers_twin_skill_confidence(db):
    twin = CareerTwin(user_id="u2", full_name="X", email="", phone="", location="",
                      skills=[{"name": "verilog", "confidence": 0.6}], strengths=[])
    db.add(twin)
    await db.flush()
    await FeedbackService(db).record_feedback("u2", "rejected", skills="verilog")
    await db.refresh(twin)
    conf = next(s["confidence"] for s in twin.skills if s["name"] == "verilog")
    assert conf < 0.6


@pytest.mark.asyncio
async def test_apply_affinity_reranks(db):
    svc = FeedbackService(db)
    matches = [
        _Match(company="WebCo", total_score=70, matched_skills=["react"]),
        _Match(company="Bosch", total_score=68, matched_skills=["can"]),
    ]
    ranked = svc.apply_affinity(matches, {"can": 1.0, "react": -1.0}, {"bosch": 0.5})
    assert ranked[0].company == "Bosch"
    assert ranked[0].rank == 1


@pytest.mark.asyncio
async def test_feedback_without_twin_is_safe(db):
    # no twin for u3 → must not raise
    out = await FeedbackService(db).record_feedback("u3", "interview", skills="c")
    assert out["feedback_type"] == "interview"
