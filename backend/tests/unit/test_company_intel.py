"""Unit tests for Module 7 — company intelligence (profiles + live stats)."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.company.intelligence import REGISTRY
from app.company.profiles import PROFILES, all_profiles, get_profile
from app.database.base import Base
from app.services.company_intel_service import CompanyIntelligenceService
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


def test_every_registry_company_has_profile():
    assert len(PROFILES) == len({t.name.lower() for t in REGISTRY})
    assert len(PROFILES) >= 55
    for t in REGISTRY:
        p = get_profile(t.name)
        assert p is not None
        assert p.tech_stack and p.embedded_domains and p.prep_focus
        assert p.salary_max_lpa >= p.salary_min_lpa > 0


def test_override_applied_for_marquee():
    q = get_profile("Qualcomm")
    assert "hexagon dsp" in q.tech_stack
    assert q.salary_max_lpa >= 60


def test_tier_default_for_non_override():
    # a tier1 company without explicit override still gets tier defaults
    p = get_profile("ARM")
    assert p.interview_difficulty == "very_high"
    assert "c" in p.tech_stack


@pytest.mark.asyncio
async def test_get_company_intel_unknown(db):
    out = await CompanyIntelligenceService(db).get_company_intel("NoSuchCo")
    assert out["found"] is False


@pytest.mark.asyncio
async def test_get_company_intel_includes_stats(db):
    out = await CompanyIntelligenceService(db).get_company_intel("Bosch")
    assert out["found"] is True
    assert out["application_stats"]["applications"] == 0
    assert out["application_stats"]["call_rate"] == 0.0


@pytest.mark.asyncio
async def test_success_stats_from_feedback(db):
    fb = FeedbackService(db)
    await fb.record_feedback("u1", "applied", company="Bosch", skills="c,can")
    await fb.record_feedback("u1", "applied", company="Bosch", skills="c")
    await fb.record_feedback("u1", "interview", company="Bosch", skills="c,can")
    await fb.record_feedback("u1", "offer", company="Bosch", skills="c")
    out = await CompanyIntelligenceService(db).get_company_intel("Bosch")
    stats = out["application_stats"]
    assert stats["applications"] == 2
    assert stats["calls"] == 2  # interview + offer
    assert stats["offers"] == 1
    assert stats["call_rate"] == 1.0
    assert stats["offer_rate"] == 0.5


@pytest.mark.asyncio
async def test_list_companies_and_tier_filter(db):
    svc = CompanyIntelligenceService(db)
    all_out = await svc.list_companies()
    assert all_out["total"] >= 55
    tier1 = await svc.list_companies(tier="tier1_semiconductor")
    assert tier1["total"] >= 1
    assert all(c["tier"] == "tier1_semiconductor" for c in tier1["companies"])


def test_profiles_ordered_by_priority():
    ordered = all_profiles()
    assert ordered == sorted(ordered, key=lambda p: p.priority, reverse=True)
