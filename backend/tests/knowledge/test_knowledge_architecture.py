"""EMBEDHUNT AI — Knowledge Architecture tests.

Runs against in-memory SQLite seeded with a realistic user (User + Profile +
Career Twin + roadmap + checkins + recommendation) plus the knowledge-graph
seed. Covers the layer registry, KnowledgeContext rendering, assembler
dependency-ordered composition against real data, empty-user graceful skipping,
the planned Health layer, and the orchestrator hand-off (grounding via
context["system"], PII-light).
"""
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM tables
from app.database.base import Base
from app.knowledge import (
    KnowledgeAssembler,
    KnowledgeContext,
    KnowledgeLayer,
    KnowledgeService,
    ordered_layers,
)
from app.knowledge.layers import IMPLEMENTED, LAYER_SPECS, PLANNED
from app.models.career_twin import CareerTwin
from app.models.daily_checkin import DailyCheckin
from app.models.profile import CandidateProfile
from app.models.recommendation import JobRecommendation
from app.models.roadmap import LearningRoadmap
from app.models.user import User
from database.seeds.knowledge_graph_seed import seed_knowledge_graph

USER_ID = "user-knowledge-1"


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _seed_full_user(s: AsyncSession) -> None:
    await seed_knowledge_graph(s)  # skill graph for Skills/KnowledgeGraph layers
    s.add(User(
        id=USER_ID, email="jane@example.com", username="jane", password_hash="x",
        first_name="Jane", last_name="Doe", target_salary_lpa=30.0, min_salary_lpa=20.0,
    ))
    s.add(CandidateProfile(
        user_id=USER_ID, headline="Embedded Firmware Engineer",
        total_experience_years=5.0, profile_score=72, is_actively_looking=True,
    ))
    s.add(CareerTwin(
        user_id=USER_ID,
        full_name="Jane Doe", email="jane@example.com", phone="+1 415 555 1234",
        skills=[{"name": "CAN", "confidence": 0.9}, {"name": "Embedded C", "confidence": 0.9},
                {"name": "RTOS", "confidence": 0.7}],
        current_role="Firmware Engineer", current_company="Bosch",
        current_salary_lpa=22.0, target_salary_lpa=30.0, min_salary_lpa=20.0,
        career_level="mid", embedded_domain_score=68, market_value_score=64,
        dream_companies=["NVIDIA", "Qualcomm"], projects=[{"name": "BMS firmware"}, {"name": "CAN gateway"}],
        career_goals={"target_role": "AUTOSAR Engineer", "short_term": "Learn AUTOSAR",
                      "long_term": "Functional safety lead"},
        learning_streak_days=4, interviews_completed=2, avg_interview_score=71.0,
        interview_readiness_score=60, weak_interview_topics=["MCAL", "diagnostics"],
        skills_learned_this_month=["RTOS"], version=3,
    ))
    s.add(LearningRoadmap(
        user_id=USER_ID, target_job_title="AUTOSAR Engineer", progress_pct=25,
        total_gap_skills=5, estimated_weeks=12, is_active=True,
    ))
    s.add(JobRecommendation(
        user_id=USER_ID, job_id="j1", job_title="AUTOSAR Developer", company_name="NVIDIA",
        match_score=82,
    ))
    today = date.today()
    for i in range(3):  # 3-day streak ending today
        s.add(DailyCheckin(user_id=USER_ID, checkin_date=(today - timedelta(days=i)).isoformat(),
                           tasks_completed=2))
    await s.flush()


# ── layer registry ──────────────────────────────────────────────────────────
def test_sixteen_layers_in_dependency_order():
    layers = ordered_layers()
    assert len(layers) == 16
    assert layers[0] == KnowledgeLayer.USER
    assert layers[1] == KnowledgeLayer.CAREER_TWIN
    assert layers[-1] == KnowledgeLayer.PROFESSIONAL_GROWTH
    # Knowledge Graph sits above Skills (deterministic answers before personalisation).
    assert layers.index(KnowledgeLayer.KNOWLEDGE_GRAPH) < layers.index(KnowledgeLayer.SKILLS)


def test_only_health_is_planned():
    planned = [l for l, spec in LAYER_SPECS.items() if spec.status == PLANNED]
    assert planned == [KnowledgeLayer.HEALTH]
    assert LAYER_SPECS[KnowledgeLayer.USER].status == IMPLEMENTED


# ── KnowledgeContext rendering ──────────────────────────────────────────────
def test_context_set_get_and_brief():
    ctx = KnowledgeContext(user_id="u")
    from app.knowledge.base import LayerData

    ctx.set_layer(KnowledgeLayer.USER, LayerData(layer="user", summary="Engineer · 5y"))
    ctx.set_layer(KnowledgeLayer.SKILLS, LayerData(layer="skills", summary="3 skills"))
    ctx.mark_skipped(KnowledgeLayer.HEALTH, "planned")

    assert ctx.user.summary == "Engineer · 5y"
    assert ctx.loaded == ["user", "skills"]  # dependency order
    brief = ctx.to_brief()
    assert "User: Engineer · 5y" in brief
    assert brief.index("User") < brief.index("Skills")  # ordered
    assert ctx.skipped["health"] == "planned"


# ── assembler against real data ─────────────────────────────────────────────
async def test_assembles_all_backed_layers(session):
    await _seed_full_user(session)
    ctx = await KnowledgeAssembler().assemble(USER_ID, session)

    # Every implemented layer should load for a fully-populated user...
    for layer in [KnowledgeLayer.USER, KnowledgeLayer.CAREER_TWIN, KnowledgeLayer.KNOWLEDGE_GRAPH,
                  KnowledgeLayer.SKILLS, KnowledgeLayer.COMPANIES, KnowledgeLayer.JOBS,
                  KnowledgeLayer.PROJECTS, KnowledgeLayer.LEARNING, KnowledgeLayer.INTERVIEW,
                  KnowledgeLayer.SALARY, KnowledgeLayer.GOALS, KnowledgeLayer.HABITS,
                  KnowledgeLayer.PROFESSIONAL_GROWTH]:
        assert layer.value in ctx.layers, f"{layer.value} should have loaded"
    # ...and Health (planned, no provider) is skipped.
    assert ctx.skipped.get("health") == "planned"
    assert ctx.assembled_at is not None


async def test_skills_layer_uses_graph_for_gaps(session):
    await _seed_full_user(session)
    ctx = await KnowledgeAssembler().assemble(USER_ID, session)
    skills = ctx.skills
    assert skills is not None
    assert skills.facts["target_role"] == "AUTOSAR Engineer"
    # Graph knows AUTOSAR Engineer requires AUTOSAR/MCAL/BSW/RTE, none of which the user has.
    missing = set(skills.facts["missing"])
    assert {"AUTOSAR", "MCAL", "BSW", "RTE"} <= missing
    assert "CAN" not in missing  # already known


async def test_habits_streak_and_salary_reads_market(session):
    await _seed_full_user(session)
    ctx = await KnowledgeAssembler().assemble(USER_ID, session)
    assert ctx.habits.facts["current_streak_days"] == 3
    assert ctx.salary.facts["target_lpa"] == 30.0


async def test_downstream_reuses_stashed_twin(session):
    await _seed_full_user(session)
    ctx = await KnowledgeAssembler().assemble(USER_ID, session)
    # CareerTwinProvider stashes the ORM twin; downstream providers reuse it.
    assert ctx.stashed("career_twin_obj") is not None


async def test_layer_subset_only_loads_requested(session):
    await _seed_full_user(session)
    ctx = await KnowledgeAssembler().assemble(
        USER_ID, session, layers=[KnowledgeLayer.USER, KnowledgeLayer.CAREER_TWIN]
    )
    assert set(ctx.layers) == {"user", "career_twin"}


# ── empty user degrades gracefully ──────────────────────────────────────────
async def test_empty_user_skips_all_without_error(session):
    ctx = await KnowledgeAssembler().assemble("ghost-user", session)
    assert ctx.layers == {}
    assert ctx.skipped["user"] == "no_data"
    assert ctx.skipped["health"] == "planned"
    assert ctx.to_brief() == ""


# ── orchestrator hand-off ───────────────────────────────────────────────────
async def test_orchestrator_context_is_grounded_and_pii_light(session):
    await _seed_full_user(session)
    ctx = await KnowledgeAssembler().assemble(USER_ID, session)

    handoff = KnowledgeService.orchestrator_context(ctx, session=session)

    assert handoff["user_id"] == USER_ID
    assert handoff["db"] is session
    system = handoff["system"]
    # Grounded in the user's real data...
    assert "AUTOSAR Engineer" in system
    assert "skills" in system.lower()
    # ...but PII-light: no raw email or phone from the Career Twin leaks in.
    assert "jane@example.com" not in system
    assert "555 1234" not in system


async def test_orchestrator_context_empty_when_no_knowledge(session):
    ctx = await KnowledgeAssembler().assemble("ghost-user", session)
    handoff = KnowledgeService.orchestrator_context(ctx)
    assert "system" not in handoff  # nothing to ground on
    assert handoff["user_id"] == "ghost-user"
