"""Unit tests for Module 10 — interview engine (500+ Qs) + mock service."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.interview_engine import InterviewEngine, get_interview_engine
from app.database.base import Base
from app.interview.question_bank_extended import ALL_QUESTIONS, count
from app.models.career_twin import CareerTwin
from app.services.mock_interview_service import MockInterviewService

import app.models  # noqa: F401


# ── question bank ────────────────────────────────────────────────────────────

def test_bank_has_500_plus_unique_questions():
    assert count() >= 500
    ids = [q["id"] for q in ALL_QUESTIONS]
    texts = [q["q"].lower() for q in ALL_QUESTIONS]
    assert len(ids) == len(set(ids))
    assert len(texts) == len(set(texts))


def test_every_question_well_formed():
    for q in ALL_QUESTIONS:
        assert q["q"] and q["skill"] and q["difficulty"] in {"easy", "medium", "hard"}
        assert q["type"]


# ── engine: session building ─────────────────────────────────────────────────

def test_build_session_count_and_balance():
    eng = InterviewEngine()
    session = eng.build_session(["c", "freertos", "can"], count=9)
    assert len(session) == 9
    skills = {q.skill for q in session}
    assert len(skills) >= 2  # balanced across skills


def test_weak_skills_get_more_questions():
    eng = InterviewEngine()
    session = eng.build_session(["c", "autosar"], count=8, weak_skills=["autosar"])
    counts = {}
    for q in session:
        counts[q.skill] = counts.get(q.skill, 0) + 1
    assert counts.get("autosar", 0) >= counts.get("c", 0)


# ── engine: scoring ──────────────────────────────────────────────────────────

def test_score_answer_keyword_match():
    eng = InterviewEngine()
    q = next(x for x in ALL_QUESTIONS if x["skill"] == "c" and x.get("expected"))
    good = eng.score_answer(q["id"], q["expected"] + " and more detail about pointers memory")
    empty = eng.score_answer(q["id"], "")
    assert good.score > empty.score
    assert empty.score == 0


def test_score_unknown_question():
    eng = InterviewEngine()
    s = eng.score_answer("nope", "anything")
    assert s.score == 0


def test_evaluate_readiness_and_weakness():
    eng = InterviewEngine()
    session = eng.build_session(["c", "freertos"], count=4)
    answers = {}
    for i, q in enumerate(session):
        # answer first well (use expected), leave others weak
        answers[q.id] = q.expected if i == 0 else "i don't know"
    ev = eng.evaluate(answers)
    assert 0 <= ev.readiness_score <= 100
    assert ev.total == len(answers)
    assert ev.weak_skills  # some skills answered poorly


def test_singleton_accessor():
    assert get_interview_engine() is get_interview_engine()


# ── service ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_service_generate_with_explicit_skills(db):
    out = await MockInterviewService(db).generate("u1", skills=["c", "can"], count=6)
    assert out["total_questions"] == 6
    assert out["session_id"]
    assert all("expected" not in q for q in out["questions"])  # answers hidden


@pytest.mark.asyncio
async def test_service_generate_uses_twin_and_evaluate_feeds_back(db):
    twin = CareerTwin(user_id="u2", full_name="Ram", email="", phone="", location="",
                      skills=[{"name": "c", "confidence": 0.9},
                              {"name": "autosar", "confidence": 0.3}],
                      known_weaknesses=[], strengths=[], interview_history=[])
    db.add(twin)
    await db.flush()

    svc = MockInterviewService(db)
    gen = await svc.generate("u2", count=6)
    assert "autosar" in gen["focus_weak_skills"]

    # answer everything poorly → autosar becomes a weak topic fed to the twin
    answers = {q["id"]: "no idea" for q in gen["questions"]}
    ev = await svc.evaluate("u2", gen["session_id"], answers)
    assert ev["session_id"] == gen["session_id"]
    await db.refresh(twin)
    assert (twin.interview_history or [])  # interview result recorded on twin


@pytest.mark.asyncio
async def test_generate_requires_skills_or_twin(db):
    with pytest.raises(Exception):
        await MockInterviewService(db).generate("nouser")
