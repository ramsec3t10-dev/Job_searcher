"""EMBEDHUNT AI — Knowledge Graph engine + repository + seed tests.

Runs against an in-memory SQLite database seeded via the idempotent seed script
(no Postgres, no Bedrock). Covers graph traversal correctness for the seeded
chain, the engine's confidence=1.0 answers vs confidence=None fallthrough,
orchestrator routing (KG hit skips Claude; unknown skill falls through to
Claude), and seed idempotency.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM tables
from app.database.base import Base
from app.models.knowledge_graph import RoleRequirement, SkillEdge, SkillNode
from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine
from app.orchestrator.rule_engine import RuleEngine
from app.orchestrator.router import Orchestrator
from app.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from database.seeds.knowledge_graph_seed import seed_knowledge_graph


@pytest_asyncio.fixture
async def seeded_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        await seed_knowledge_graph(session)
        await session.commit()
        yield session
    await engine.dispose()


def _names(nodes):
    return [n.name for n in nodes]


# ── Repository traversal ────────────────────────────────────────────────────
async def test_learning_path_follows_seeded_chain(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    path = await repo.get_learning_path("CAN", "AUTOSAR")
    assert _names(path) == ["CAN", "RTOS", "MCAL", "BSW", "AUTOSAR"]


async def test_prerequisites_ordered_foundational_first(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    prereqs = _names(await repo.get_prerequisites("AUTOSAR"))
    # Target itself is never a prerequisite of itself.
    assert "AUTOSAR" not in prereqs
    # The prescribed chain appears, foundational → advanced.
    for earlier, later in [("CAN", "RTOS"), ("RTOS", "MCAL"), ("MCAL", "BSW")]:
        assert prereqs.index(earlier) < prereqs.index(later)


async def test_next_skills_after_rtos(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    assert _names(await repo.get_next_skills("RTOS")) == ["MCAL"]


async def test_role_requirements_required_only(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    required = _names(await repo.get_role_requirements("AUTOSAR Engineer"))
    assert {"AUTOSAR", "MCAL", "BSW", "RTE", "CAN", "Embedded C"} <= set(required)
    # Recommended (required=False) skills are excluded from the strict list.
    assert "Functional Safety (ISO 26262)" not in required


async def test_role_requirement_details_splits_required_and_recommended(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    details = await repo.get_role_requirement_details("AUTOSAR Engineer")
    required = {n.name for n, req in details if req}
    recommended = {n.name for n, req in details if not req}
    assert "AUTOSAR" in required
    assert {"Functional Safety (ISO 26262)", "ASPICE"} <= recommended


async def test_unknown_skill_has_no_prerequisites(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    assert await repo.get_prerequisites("Rust") == []
    assert await repo.get_learning_path("Rust", "AUTOSAR") == []


async def test_no_backward_path_returns_empty(seeded_session):
    repo = KnowledgeGraphRepository(seeded_session)
    # Edges are directed; there is no forward path from AUTOSAR back to CAN.
    assert await repo.get_learning_path("AUTOSAR", "CAN") == []


# ── Engine behaviour (confidence 1.0 vs None fallthrough) ───────────────────
async def test_engine_answers_prerequisites(seeded_session):
    engine = KnowledgeGraphEngine()
    result = await engine.run(
        "skill_query", {"query": "what does AUTOSAR require?"}, {"db": seeded_session}
    )
    assert result.confidence == 1.0
    assert result.engine_used == "knowledge_graph"
    assert result.cost_estimate_usd == 0.0
    assert "CAN" in result.text and "BSW" in result.text


async def test_engine_answers_next_skills(seeded_session):
    engine = KnowledgeGraphEngine()
    result = await engine.run(
        "skill_query", {"query": "what should I learn after RTOS?"}, {"db": seeded_session}
    )
    assert result.confidence == 1.0
    assert "MCAL" in result.text


async def test_engine_answers_learning_path(seeded_session):
    engine = KnowledgeGraphEngine()
    result = await engine.run(
        "learning_path", {"from_skill": "CAN", "to_skill": "AUTOSAR"}, {"db": seeded_session}
    )
    assert result.confidence == 1.0
    assert "CAN → RTOS → MCAL → BSW → AUTOSAR" in result.text


async def test_engine_answers_role_requirements(seeded_session):
    engine = KnowledgeGraphEngine()
    result = await engine.run(
        "skill_query", {"role": "AUTOSAR Engineer"}, {"db": seeded_session}
    )
    assert result.confidence == 1.0
    assert "Required" in result.text and "AUTOSAR" in result.text


async def test_engine_unknown_skill_triggers_fallthrough(seeded_session):
    engine = KnowledgeGraphEngine()
    result = await engine.run(
        "skill_query", {"query": "what comes after Rust programming?"}, {"db": seeded_session}
    )
    # Query matches no known node → confidence=None so the orchestrator falls through.
    assert result.confidence is None


async def test_engine_unsupported_task_returns_none(seeded_session):
    engine = KnowledgeGraphEngine()
    result = await engine.run("summarization", {"prompt": "hi"}, {"db": seeded_session})
    assert result is None


# ── Orchestrator routing ────────────────────────────────────────────────────
def _mock_claude():
    claude = MagicMock(spec=ClaudeEngine)
    claude.run = AsyncMock(
        return_value=EngineResult(text="from-claude", engine_used="claude:mock", cost_estimate_usd=0.01)
    )
    return claude


async def test_router_kg_hit_skips_claude(seeded_session):
    claude = _mock_claude()
    orch = Orchestrator(
        rule_engine=RuleEngine(),
        knowledge_graph_engine=KnowledgeGraphEngine(),
        cache_engine=CacheEngine(force_memory=True),
        claude_engine=claude,
    )
    result = await orch.handle(
        "skill_query", {"query": "what does AUTOSAR require?"}, {"db": seeded_session}
    )
    assert result.engine_used == "knowledge_graph"
    claude.run.assert_not_awaited()


async def test_router_kg_fallthrough_reaches_claude(seeded_session):
    claude = _mock_claude()
    orch = Orchestrator(
        rule_engine=RuleEngine(),
        knowledge_graph_engine=KnowledgeGraphEngine(),
        cache_engine=CacheEngine(force_memory=True),
        claude_engine=claude,
    )
    result = await orch.handle(
        "skill_query", {"query": "tell me about Rust programming"}, {"db": seeded_session}
    )
    # KG returned confidence=None → cache miss → Claude answered.
    assert result.engine_used == "claude:mock"
    claude.run.assert_awaited_once()


# ── Seed idempotency ────────────────────────────────────────────────────────
async def test_seed_is_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with maker() as session:
            first = await seed_knowledge_graph(session)
            await session.commit()
            # First run creates everything.
            assert first["nodes_created"] == first["nodes_total"]
            assert first["edges_created"] == first["edges_total"]
            assert first["roles_created"] == first["roles_total"]

            second = await seed_knowledge_graph(session)
            await session.commit()
            # Re-run is a no-op.
            assert second["nodes_created"] == 0
            assert second["edges_created"] == 0
            assert second["roles_created"] == 0

            # Row counts equal the totals (no duplicates).
            node_count = (await session.execute(select(func.count()).select_from(SkillNode))).scalar_one()
            edge_count = (await session.execute(select(func.count()).select_from(SkillEdge))).scalar_one()
            role_count = (await session.execute(select(func.count()).select_from(RoleRequirement))).scalar_one()
            assert node_count == first["nodes_total"]
            assert edge_count == first["edges_total"]
            assert role_count == first["roles_total"]
    finally:
        await engine.dispose()
