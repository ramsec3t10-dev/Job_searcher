"""EMBEDHUNT AI — AI Agent layer tests.

Every test mocks ``AIRouter.route`` so no network/LLM is touched, then asserts
the agent (1) sent the correct TaskType, (2) used the correct prompt's system
instruction, (3) parsed the response into the right model, and (4) stored a
memory when the pipeline requires it.
"""
import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents import (
    CodingAgent,
    InterviewAgent,
    LearningAgent,
    MatchingAgent,
    MentorAgent,
    ResumeAgent,
    RoadmapAgent,
    SalaryAgent,
)
from app.agents.models import (
    AnswerEvaluation,
    CodeReview,
    CodingChallenge,
    DailyBrief,
    GapAnalysis,
    JobMatch,
    Lesson,
    MentorResponse,
    ParsedResume,
    ResumeScore,
    RewrittenResume,
    Roadmap,
    SalaryEstimate,
)
from app.database.base import Base
from app.llm.model_selector import TaskType
from app.llm.router import AIResponse
from app.llm import prompts

# Register all tables (twin, memory, usage log, conversations) before create_all.
import app.models  # noqa: F401
from app.llm.cost_tracker import AIUsageLog  # noqa: F401
from app.llm.conversation_manager import Conversation  # noqa: F401
from app.models.career_twin import CareerTwin
from app.models.memory import MemoryEntry


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
    await engine.dispose()


def _mock_route(agent, payload: dict) -> AsyncMock:
    """Replace the agent's router.route with a mock returning ``payload`` as JSON."""
    response = AIResponse(
        content=json.dumps(payload),
        model_used="claude-haiku-4-5",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.0001,
        latency_ms=5.0,
        cached=False,
        task_type=TaskType.EXTRACTION,
    )
    mock = AsyncMock(return_value=response)
    agent.router.route = mock
    return mock


def _mock_handle(agent, payload: dict) -> AsyncMock:
    """Replace a migrated agent's orchestrator.handle with a mock returning ``payload``.

    Used for call sites migrated (Phase 4) from ``router.route`` to
    ``orchestrator.handle``.
    """
    from app.orchestrator.engine_base import EngineResult

    mock = AsyncMock(return_value=EngineResult(
        text=json.dumps(payload), engine_used="together:mock", confidence=0.9,
        cost_estimate_usd=0.0001, tokens_in=10, tokens_out=20))
    from unittest.mock import MagicMock

    agent.orchestrator = MagicMock()
    agent.orchestrator.handle = mock
    return mock


def _sent_task(mock: AsyncMock) -> TaskType:
    return mock.await_args.args[0]


def _sent_system(mock: AsyncMock) -> str:
    return mock.await_args.args[2]


# Accessors for the migrated orchestrator path: handle(task, payload, context).
def _handle_task(mock: AsyncMock) -> str:
    return mock.await_args.args[0]


def _handle_system(mock: AsyncMock) -> str:
    return mock.await_args.args[1]["system"]


def _handle_user_id(mock: AsyncMock) -> str:
    return mock.await_args.args[2]["user_id"]


async def _memory_count(db, user_id: str, memory_type: str) -> int:
    stmt = select(func.count()).select_from(MemoryEntry).where(
        MemoryEntry.user_id == user_id, MemoryEntry.memory_type == memory_type
    )
    return (await db.execute(stmt)).scalar_one()


def _twin() -> CareerTwin:
    return CareerTwin(
        user_id="u1", full_name="Ram", current_role="Embedded Engineer",
        career_level="senior", total_years_experience=6.0, location="Bengaluru",
        current_salary_lpa=28.0, target_salary_lpa=40.0, learning_velocity=1.2,
        skills=[{"name": "C", "confidence": 0.9, "depth": "expert", "years_used": 6, "recency_score": 1.0}],
        interview_history=[], known_weaknesses=["system design"],
    )


# ── ResumeAgent ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_resume_agent_parse(db):
    agent = ResumeAgent(db)
    mock = _mock_handle(agent, {
        "skills": ["c", "can", "freertos"], "total_years": 6,
        "contact": {"name": "Ram", "email": "r@x.com", "phone": "1"},
    })
    result = await agent.parse("resume text", "u1")

    assert isinstance(result, ParsedResume)
    assert _handle_task(mock) == "resume_parsing"
    assert _handle_system(mock) == prompts.RESUME_PARSER.system_prompt
    assert result.skills == ["c", "can", "freertos"]
    assert await _memory_count(db, "u1", "resume") == 1


@pytest.mark.asyncio
async def test_resume_agent_score(db):
    agent = ResumeAgent(db)
    mock = _mock_handle(agent, {"score": 72, "ats_score": 65})
    result = await agent.score("resume", "job desc", "u1")

    assert isinstance(result, ResumeScore)
    assert _handle_task(mock) == "resume_score"
    assert _handle_system(mock) == prompts.RESUME_SCORER.system_prompt
    assert result.score == 72


@pytest.mark.asyncio
async def test_resume_agent_rewrite(db):
    agent = ResumeAgent(db)
    mock = _mock_handle(agent, {"rewritten_bullets": ["did x"], "estimated_score_improvement": 15})
    result = await agent.rewrite("resume", {"description": "job"}, _twin(), "u1")

    assert isinstance(result, RewrittenResume)
    assert _handle_task(mock) == "resume_rewrite"
    assert _handle_system(mock) == prompts.RESUME_REWRITER.system_prompt


# ── MatchingAgent ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_matching_agent_match(db):
    # Phase 4: match() now routes through the orchestrator (task match_explanation).
    agent = MatchingAgent(db)
    mock = _mock_handle(agent, {"score": 80, "recommended_action": "apply_now", "missing_skills": ["autosar"]})
    result = await agent.match(_twin(), {"title": "FW Eng", "required_skills": ["c"]}, "u1")

    assert isinstance(result, JobMatch)
    assert mock.await_args.args[0] == "match_explanation"          # orchestrator task
    assert mock.await_args.args[1]["system"] == prompts.JOB_MATCH.system_prompt
    assert mock.await_args.args[2]["user_id"] == "u1"              # cost attribution
    assert result.score == 80                                     # shape unchanged


@pytest.mark.asyncio
async def test_matching_agent_analyze_gaps(db):
    # Phase 4: routes through the orchestrator (gap_analysis_explanation → Claude tier).
    agent = MatchingAgent(db)
    mock = _mock_handle(agent, {"critical_gaps": ["autosar"], "immediate_focus": "autosar"})
    result = await agent.analyze_gaps(_twin(), {"title": "FW Eng"}, "u1")

    assert isinstance(result, GapAnalysis)
    assert _handle_task(mock) == "gap_analysis_explanation"
    assert _handle_system(mock) == prompts.GAP_ANALYSIS.system_prompt
    assert _handle_user_id(mock) == "u1"


# ── MentorAgent ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_mentor_agent_advise(db):
    agent = MentorAgent(db)
    mock = _mock_handle(agent, {"advice": "Focus on AUTOSAR", "action_items": ["study bsw"], "priority": "high"})
    result = await agent.advise("u1", "How do I grow?", "conv1")

    assert isinstance(result, MentorResponse)
    assert _handle_task(mock) == "mentor_chat"
    assert _handle_system(mock) == prompts.CAREER_ADVICE.system_prompt
    assert result.advice == "Focus on AUTOSAR"
    assert await _memory_count(db, "u1", "conversation") == 1
    # Both the user turn and the assistant reply were persisted.
    convo = (await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.conversation_id == "conv1")
    )).scalar_one()
    assert convo == 2


@pytest.mark.asyncio
async def test_mentor_agent_daily_brief(db):
    agent = MentorAgent(db)
    mock = _mock_handle(agent, {"greeting": "Morning", "focus_skill": "can", "new_jobs_count": 3})
    result = await agent.daily_brief("u1")

    assert isinstance(result, DailyBrief)
    assert _handle_task(mock) == "mentor_daily_brief"
    assert _handle_system(mock) == prompts.DAILY_BRIEF.system_prompt


# ── InterviewAgent ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_interview_agent_generate_questions(db):
    agent = InterviewAgent(db)
    mock = _mock_handle(agent, {"questions": [
        {"text": "Explain CAN arbitration", "type": "conceptual", "difficulty": "medium"},
    ]})
    result = await agent.generate_questions("u1", "can", "Bosch", "medium")

    assert isinstance(result, list)
    assert result[0].text == "Explain CAN arbitration"
    assert _handle_task(mock) == "interview_questions"
    assert _handle_system(mock) == prompts.QUESTION_GENERATOR.system_prompt


@pytest.mark.asyncio
async def test_interview_agent_evaluate_answer(db):
    agent = InterviewAgent(db)
    mock = _mock_handle(agent, {"score": 70, "what_was_missing": "edge cases", "feedback": "ok"})
    result = await agent.evaluate_answer("u1", "Q?", "A.", "can")

    assert isinstance(result, AnswerEvaluation)
    assert _handle_task(mock) == "interview_evaluation"
    assert _handle_system(mock) == prompts.ANSWER_EVALUATOR.system_prompt
    assert result.score == 70
    assert await _memory_count(db, "u1", "interview") == 1


@pytest.mark.asyncio
async def test_interview_agent_evaluate_updates_twin(db):
    # Seed a twin so evaluate_answer folds the score back in.
    from app.services.career_twin_service import CareerTwinService
    svc = CareerTwinService(db)
    await svc.get_or_create("u2")

    agent = InterviewAgent(db)
    _mock_handle(agent, {"score": 55, "what_was_missing": "timing", "feedback": "x"})
    await agent.evaluate_answer("u2", "Q?", "A.", "rtos")

    twin = await agent.twin_repo.get_by_user("u2")
    assert twin.interviews_completed == 1
    assert twin.avg_interview_score == 55.0


# ── RoadmapAgent ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_roadmap_agent_generate(db):
    agent = RoadmapAgent(db)
    mock = _mock_handle(agent, {"weeks": [{"number": 1, "skill": "autosar"}], "total_weeks": 8})
    result = await agent.generate("u1", {"title": "Senior FW Eng", "required_skills": ["autosar"]}, 10)

    assert isinstance(result, Roadmap)
    assert _handle_task(mock) == "roadmap_draft"
    assert _handle_system(mock) == prompts.ROADMAP_GENERATOR.system_prompt
    assert result.total_weeks == 8
    assert await _memory_count(db, "u1", "learning") == 1


# ── SalaryAgent ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_salary_agent_estimate(db):
    agent = SalaryAgent(db)
    mock = _mock_handle(agent, {"estimated_min_lpa": 25, "estimated_max_lpa": 40, "percentile": 60})
    result = await agent.estimate("u1", "NXP")

    assert isinstance(result, SalaryEstimate)
    assert _handle_task(mock) == "salary_estimate"
    assert _handle_system(mock) == prompts.SALARY_ESTIMATOR.system_prompt
    assert result.estimated_max_lpa == 40


# ── LearningAgent ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_learning_agent_create_lesson(db):
    agent = LearningAgent(db)
    mock = _mock_handle(agent, {"topic": "CAN bus", "explanation": "..."})
    result = await agent.create_lesson("u1", "can", "arbitration")

    assert isinstance(result, Lesson)
    assert _handle_task(mock) == "lesson_generation"
    assert _handle_system(mock) == prompts.LESSON_GENERATOR.system_prompt


@pytest.mark.asyncio
async def test_learning_agent_create_flashcards(db):
    agent = LearningAgent(db)
    mock = _mock_handle(agent, {"cards": [{"front": "What is CAN?", "back": "A bus", "difficulty": "easy"}]})
    result = await agent.create_flashcards("u1", "can")

    assert isinstance(result, list)
    assert result[0].front == "What is CAN?"
    assert _handle_task(mock) == "flashcard_generation"
    assert _handle_system(mock) == prompts.FLASHCARD_GENERATOR.system_prompt


# ── CodingAgent ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_coding_agent_review_code(db):
    agent = CodingAgent(db)
    mock = _mock_handle(agent, {"overall_score": 75, "memory_issues": ["leak at line 5"]})
    result = await agent.review_code("u1", "int main(){return 0;}", "c")

    assert isinstance(result, CodeReview)
    assert _handle_task(mock) == "coding_review_explanation"
    assert _handle_system(mock) == prompts.CODE_REVIEWER.system_prompt
    assert result.overall_score == 75
    # Token efficiency: only code + language + empty context sent, no twin data.
    assert "system design" not in _handle_system(mock)


@pytest.mark.asyncio
async def test_coding_agent_generate_challenge(db):
    agent = CodingAgent(db)
    mock = _mock_handle(agent, {"title": "Ring buffer", "difficulty": "medium"})
    result = await agent.generate_challenge("u1", "data structures", "medium")

    assert isinstance(result, CodingChallenge)
    assert _handle_task(mock) == "coding_challenge"
    assert _handle_system(mock) == prompts.CHALLENGE_GENERATOR.system_prompt
    assert result.title == "Ring buffer"
