"""EMBEDHUNT AI — Career Twin Service (Phase 3) tests."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.resume.extractor import extract_skills, extract_experience
from app.resume.normalizer import build_profile
from app.services.career_twin_service import CareerTwinService

import app.models  # noqa: F401 — register tables

SAMPLE_RESUME = """
Ram Kumar
ram.kumar@example.com  +91 9876543210

Senior Embedded Software Engineer at Bosch

Experience
Bosch Global Software Technologies  2019 - present
Embedded firmware in C and C++ on ARM Cortex-M. AUTOSAR Classic BSW, CAN, LIN,
SPI, I2C, FreeRTOS, ISO 26262 ASIL-D, MISRA C, device driver development.

Education
B.E. Electronics, 2018
"""


def _profile():
    skills = extract_skills(SAMPLE_RESUME)
    exp = extract_experience(SAMPLE_RESUME)
    return build_profile(SAMPLE_RESUME, skills, exp)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _seed(db) -> CareerTwinService:
    from app.models.resume import Resume, ResumeStatus

    resume = Resume(
        user_id="u1", name="cv", file_url="local://x", file_name="cv.txt",
        file_type="txt", is_primary=True, status=ResumeStatus.PARSED,
        ai_summary=_profile().to_json(),
    )
    db.add(resume)
    await db.flush()
    svc = CareerTwinService(db)
    await svc.init_from_resume("u1", resume.id)
    return svc


@pytest.mark.asyncio
async def test_init_from_resume_creates_twin_with_fields(db):
    svc = await _seed(db)
    twin = await svc.get_twin("u1")
    assert twin.user_id == "u1"
    assert twin.full_name == "Ram Kumar"
    assert len(twin.skills) > 0
    assert twin.career_level in {"junior", "mid", "senior", "lead", "principal"}
    assert twin.total_years_experience > 0


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(db):
    svc = await _seed(db)
    twin1 = await svc.get_or_create("u1")
    twin2 = await svc.get_or_create("u1")
    assert twin1.id == twin2.id


@pytest.mark.asyncio
async def test_get_or_create_makes_empty_twin(db):
    svc = CareerTwinService(db)
    twin = await svc.get_or_create("new_user")
    assert twin.user_id == "new_user"
    assert twin.version == 1


@pytest.mark.asyncio
async def test_update_after_interview_updates_scores(db):
    svc = await _seed(db)
    await svc.update_after_interview("u1", {
        "company": "Bosch", "role": "Embedded Engineer", "outcome": "rejected",
        "weak_topics": ["can"], "strong_topics": ["c"], "score": 60,
    })
    await svc.update_after_interview("u1", {
        "company": "NXP", "role": "Firmware Engineer", "outcome": "passed",
        "weak_topics": ["rtos"], "strong_topics": ["c"], "score": 80,
    })
    twin = await svc.get_twin("u1")
    assert twin.interviews_completed == 2
    assert twin.avg_interview_score == 70.0
    assert "can" in twin.weak_interview_topics
    assert "rtos" in twin.weak_interview_topics


@pytest.mark.asyncio
async def test_update_after_learning_tracks_streak_and_month(db):
    svc = await _seed(db)
    await svc.update_after_learning("u1", "Rust", {"score": 90})
    twin = await svc.get_twin("u1")
    assert twin.learning_streak_days == 1
    assert any(e["skill"] == "Rust" for e in twin.skills_learned_this_month)
    assert twin.last_active_date is not None
    assert any(s["name"] == "Rust" for s in twin.skills)


@pytest.mark.asyncio
async def test_recompute_scores_within_range(db):
    svc = await _seed(db)
    twin = await svc.recompute_scores("u1")
    for field in (
        "embedded_domain_score", "profile_completeness",
        "interview_readiness_score", "market_value_score",
    ):
        value = getattr(twin, field)
        assert 0 <= value <= 100, f"{field}={value} out of range"


@pytest.mark.asyncio
async def test_get_summary_alias(db):
    svc = await _seed(db)
    summary = await svc.get_summary("u1")
    assert summary["full_name"] == "Ram Kumar"
    assert "top_skills" in summary
