"""Cross-application common skill-gap roadmap: gaps ranked by how many of the
user's APPLIED jobs demanded them; original top-matches fallback preserved."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.models.application import Application, ApplicationOutcome, ApplicationStatus
from app.services.roadmap_service import RoadmapService


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


def _app(user_id: str, title: str, missing: str) -> Application:
    return Application(user_id=user_id, job_id=f"j-{title}", resume_id="r1",
                       job_title=title, company_name="Acme", company_tier="other",
                       location="Remote", apply_url="", source_portal="test",
                       match_score=70, matched_skills="", missing_skills=missing,
                       ai_explanation="", resume_version_name="",
                       status=ApplicationStatus.QUEUED,
                       outcome=ApplicationOutcome.PENDING)


@pytest.mark.asyncio
async def test_common_gaps_ranked_by_frequency(db):
    for title, missing in [("Backend Engineer", "kubernetes, system design, go"),
                           ("Platform Engineer", "kubernetes, terraform"),
                           ("SRE", "kubernetes, system design")]:
        db.add(_app("u1", title, missing))
    await db.flush()
    ranked, n = await RoadmapService(db)._applied_common_gaps("u1")
    assert n == 3
    assert ranked[0] == "kubernetes"          # missing in all 3 applied jobs
    assert ranked[1] == "system design"       # missing in 2
    assert set(ranked[2:]) == {"go", "terraform"}


@pytest.mark.asyncio
async def test_duplicate_skill_within_one_application_counts_once(db):
    db.add(_app("u2", "Backend", "sql, sql, SQL"))
    await db.flush()
    ranked, n = await RoadmapService(db)._applied_common_gaps("u2")
    assert n == 1 and ranked == ["sql"]


@pytest.mark.asyncio
async def test_no_applications_yields_empty(db):
    ranked, n = await RoadmapService(db)._applied_common_gaps("nobody")
    assert n == 0 and ranked == []
