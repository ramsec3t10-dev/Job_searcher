"""Integration tests — AI feature endpoints (/api/v1/ai/*).

All agents are mocked; the app runs against an in-memory (AsyncMock) DB so no
network/LLM/database access occurs. Covers the Phase-6 contract:
  * auth required on every endpoint,
  * budget exceeded  -> 429 envelope,
  * master toggle off -> 503 envelope,
  * agent failure     -> 503 uniform error envelope,
  * successful calls  -> correct response schema,
  * mentor rate-limit enforced.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.auth.jwt import create_access_token
from app.config.settings import settings
from app.llm.cost_tracker import CostTracker
import app.database.session as db_session
import app.api.v1.ai_features as aif

from app.agents.models import (
    MentorResponse, DailyBrief, BriefItem, ResumeScore, RewrittenResume,
    InterviewQuestion, AnswerEvaluation, Lesson, Flashcard,
    SalaryEstimate, CodeReview, CodingChallenge,
)

API = "/api/v1/ai"
USER_ID = "user-ai-test"


# ── Fakes ────────────────────────────────────────────────────────────────────
class FakeMentorAgent:
    def __init__(self, db): ...
    async def advise(self, user_id, message, conversation_id):
        return MentorResponse(advice="Focus on RTOS fundamentals.",
                              action_items=["Build an RTOS demo"],
                              priority="high", timeframe="2 weeks")
    async def daily_brief(self, user_id):
        return DailyBrief(greeting="Morning!", focus_skill="rtos",
                          reason="High demand", new_jobs_count=4,
                          top_action="Apply to Bosch",
                          items=[BriefItem(emoji="🔥", text="New job", action_route="/jobs")])


class FailingMentorAgent:
    def __init__(self, db): ...
    async def advise(self, user_id, message, conversation_id):
        raise RuntimeError("LLM exploded")


class FakeInterviewAgent:
    def __init__(self, db): ...
    async def generate_questions(self, user_id, skill, company, difficulty, count=5):
        return [InterviewQuestion(text="What is priority inversion?", type="technical",
                                  difficulty=difficulty)]
    async def evaluate_answer(self, user_id, question, answer, skill):
        return AnswerEvaluation(score=80, technical_accuracy=85, communication=75,
                                depth=70, feedback="Solid answer.")


class FakeLearningAgent:
    def __init__(self, db): ...
    async def create_lesson(self, user_id, skill, topic):
        return Lesson(topic=topic, explanation="CAN arbitration is...",
                      key_concepts=["bit dominance"])
    async def create_flashcards(self, user_id, skill, count=10):
        return [Flashcard(front="What is a mutex?", back="A lock", difficulty="easy")]


class FakeSalaryAgent:
    def __init__(self, db): ...
    async def estimate(self, user_id, target_company=None):
        return SalaryEstimate(estimated_min_lpa=12.0, estimated_max_lpa=18.0,
                              percentile=60, is_underpaid=False)


class FakeCodingAgent:
    def __init__(self, db): ...
    async def review_code(self, user_id, code, language="c"):
        return CodeReview(overall_score=72, memory_issues=["possible leak"])
    async def generate_challenge(self, user_id, skill, difficulty):
        return CodingChallenge(title="Ring buffer", description="Implement it",
                               difficulty=difficulty)


# ── Fixtures ─────────────────────────────────────────────────────────────────
def _make_db():
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.first.return_value = None
    result.all.return_value = []
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """Clean per-test state: DB override, budget OK, feature enabled, limiter clear."""
    async def _override_db():
        yield _make_db()
    app.dependency_overrides[db_session.get_db] = _override_db

    monkeypatch.setattr(CostTracker, "is_over_budget", AsyncMock(return_value=False))
    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)

    aif._mentor_limiter._hits.clear()
    aif._brief_cache._store.clear()
    aif._salary_cache._store.clear()

    yield
    app.dependency_overrides.clear()


def _auth():
    return {"Authorization": f"Bearer {create_access_token(USER_ID, 'candidate')}"}


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# Every AI endpoint: (method, path, json-body). Used for the auth/guard matrix.
ENDPOINTS = [
    ("post", f"{API}/mentor/chat", {"message": "hi"}),
    ("get", f"{API}/mentor/daily-brief", None),
    ("post", f"{API}/resume/r1/score", {}),
    ("post", f"{API}/resume/r1/rewrite", {"job_id": "j1"}),
    ("post", f"{API}/interview/questions", {"skill": "rtos"}),
    ("post", f"{API}/interview/evaluate", {"question": "q", "answer": "a", "skill": "rtos"}),
    ("post", f"{API}/learn/lesson", {"skill": "can", "topic": "arbitration"}),
    ("post", f"{API}/learn/flashcards", {"skill": "rtos"}),
    ("get", f"{API}/salary/estimate", None),
    ("post", f"{API}/code/review", {"code": "int main(){}"}),
    ("post", f"{API}/code/challenge", {"skill": "c"}),
    ("get", f"{API}/usage", None),
]


async def _call(c, method, path, body, headers):
    if method == "get":
        return await c.get(path, headers=headers)
    return await c.post(path, json=(body or {}), headers=headers)


# ── Auth required on all endpoints ───────────────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", ENDPOINTS)
async def test_auth_required(method, path, body):
    async with _client() as c:
        r = await _call(c, method, path, body, headers=None)
    assert r.status_code in (401, 403), f"{path} should require auth, got {r.status_code}"


# ── Budget exceeded -> 429 (guarded endpoints only; /usage is exempt) ────────
@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", [e for e in ENDPOINTS if not e[1].endswith("/usage")])
async def test_budget_exceeded_returns_429(monkeypatch, method, path, body):
    monkeypatch.setattr(CostTracker, "is_over_budget", AsyncMock(return_value=True))
    async with _client() as c:
        r = await _call(c, method, path, body, headers=_auth())
    assert r.status_code == 429
    d = r.json()
    assert d["success"] is False
    assert d["error"] == "budget_exceeded"
    assert d["fallback_available"] is False
    assert "message" in d


@pytest.mark.asyncio
async def test_usage_exempt_from_budget(monkeypatch):
    """/usage must remain reachable even when the user is over budget."""
    monkeypatch.setattr(CostTracker, "is_over_budget", AsyncMock(return_value=True))
    async with _client() as c:
        r = await c.get(f"{API}/usage", headers=_auth())
    assert r.status_code == 200
    assert set(r.json()) >= {"this_month_usd", "this_month_calls",
                             "budget_remaining_usd", "breakdown_by_task"}


# ── Master toggle off -> 503 ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_disabled_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    async with _client() as c:
        r = await c.post(f"{API}/mentor/chat", json={"message": "hi"}, headers=_auth())
    assert r.status_code == 503
    d = r.json()
    assert d["success"] is False
    assert d["error"] == "ai_disabled"
    assert d["fallback_available"] is True


# ── Agent failure -> uniform 503 error envelope ──────────────────────────────
@pytest.mark.asyncio
async def test_agent_failure_error_format(monkeypatch):
    monkeypatch.setattr("app.agents.mentor_agent.MentorAgent", FailingMentorAgent)
    async with _client() as c:
        r = await c.post(f"{API}/mentor/chat", json={"message": "hi"}, headers=_auth())
    assert r.status_code == 503
    d = r.json()
    assert d == {
        "success": False,
        "error": "ai_unavailable",
        "message": "AI feature temporarily unavailable. Try again in 30 seconds.",
        "fallback_available": True,
    }


# ── Successful calls return correct schema ───────────────────────────────────
@pytest.mark.asyncio
async def test_mentor_chat_success(monkeypatch):
    monkeypatch.setattr("app.agents.mentor_agent.MentorAgent", FakeMentorAgent)
    async with _client() as c:
        r = await c.post(f"{API}/mentor/chat",
                         json={"message": "How do I get into Qualcomm?"}, headers=_auth())
    assert r.status_code == 200
    d = r.json()
    assert d["reply"] == "Focus on RTOS fundamentals."
    assert d["action_items"] == ["Build an RTOS demo"]
    assert d["conversation_id"]  # auto-generated uuid
    assert d["tokens_used"] == 0


@pytest.mark.asyncio
async def test_daily_brief_success(monkeypatch):
    monkeypatch.setattr("app.agents.mentor_agent.MentorAgent", FakeMentorAgent)
    async with _client() as c:
        r = await c.get(f"{API}/mentor/daily-brief", headers=_auth())
    assert r.status_code == 200
    d = r.json()
    assert d["focus_skill"] == "rtos"
    assert d["new_jobs_count"] == 4
    assert d["items"][0]["text"] == "New job"


@pytest.mark.asyncio
async def test_interview_questions_success(monkeypatch):
    monkeypatch.setattr("app.agents.interview_agent.InterviewAgent", FakeInterviewAgent)
    async with _client() as c:
        r = await c.post(f"{API}/interview/questions",
                         json={"skill": "rtos", "difficulty": "hard"}, headers=_auth())
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 1 and qs[0]["difficulty"] == "hard"


@pytest.mark.asyncio
async def test_interview_evaluate_success(monkeypatch):
    monkeypatch.setattr("app.agents.interview_agent.InterviewAgent", FakeInterviewAgent)
    async with _client() as c:
        r = await c.post(f"{API}/interview/evaluate",
                         json={"question": "q", "answer": "a", "skill": "rtos"}, headers=_auth())
    assert r.status_code == 200
    assert r.json()["score"] == 80


@pytest.mark.asyncio
async def test_learn_lesson_success(monkeypatch):
    monkeypatch.setattr("app.agents.learning_agent.LearningAgent", FakeLearningAgent)
    async with _client() as c:
        r = await c.post(f"{API}/learn/lesson",
                         json={"skill": "can", "topic": "CAN arbitration"}, headers=_auth())
    assert r.status_code == 200
    assert r.json()["topic"] == "CAN arbitration"


@pytest.mark.asyncio
async def test_learn_flashcards_success(monkeypatch):
    monkeypatch.setattr("app.agents.learning_agent.LearningAgent", FakeLearningAgent)
    async with _client() as c:
        r = await c.post(f"{API}/learn/flashcards", json={"skill": "rtos"}, headers=_auth())
    assert r.status_code == 200
    cards = r.json()["cards"]
    assert len(cards) == 1 and cards[0]["front"] == "What is a mutex?"


@pytest.mark.asyncio
async def test_salary_estimate_success(monkeypatch):
    monkeypatch.setattr("app.agents.salary_agent.SalaryAgent", FakeSalaryAgent)
    async with _client() as c:
        r = await c.get(f"{API}/salary/estimate", params={"company": "Bosch"}, headers=_auth())
    assert r.status_code == 200
    d = r.json()
    assert d["estimated_min_lpa"] == 12.0 and d["estimated_max_lpa"] == 18.0


@pytest.mark.asyncio
async def test_code_review_success(monkeypatch):
    monkeypatch.setattr("app.agents.coding_agent.CodingAgent", FakeCodingAgent)
    async with _client() as c:
        r = await c.post(f"{API}/code/review",
                         json={"code": "void isr(){ x=1; }", "language": "c"}, headers=_auth())
    assert r.status_code == 200
    assert r.json()["overall_score"] == 72


@pytest.mark.asyncio
async def test_code_challenge_success(monkeypatch):
    monkeypatch.setattr("app.agents.coding_agent.CodingAgent", FakeCodingAgent)
    async with _client() as c:
        r = await c.post(f"{API}/code/challenge",
                         json={"skill": "c", "difficulty": "hard"}, headers=_auth())
    assert r.status_code == 200
    assert r.json()["difficulty"] == "hard"


# ── Validation ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_mentor_chat_requires_message(monkeypatch):
    monkeypatch.setattr("app.agents.mentor_agent.MentorAgent", FakeMentorAgent)
    async with _client() as c:
        r = await c.post(f"{API}/mentor/chat", json={}, headers=_auth())
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_code_review_size_limit(monkeypatch):
    monkeypatch.setattr("app.agents.coding_agent.CodingAgent", FakeCodingAgent)
    big = "a" * (50 * 1024 + 1)
    async with _client() as c:
        r = await c.post(f"{API}/code/review", json={"code": big}, headers=_auth())
    assert r.status_code == 413


# ── Rate limiting enforced (mentor: 20 / hour) ───────────────────────────────
@pytest.mark.asyncio
async def test_mentor_rate_limit_enforced(monkeypatch):
    monkeypatch.setattr("app.agents.mentor_agent.MentorAgent", FakeMentorAgent)
    from app.api.v1.rate_limit import _limiter
    _limiter._mem.clear()
    async with _client() as c:
        for i in range(20):
            r = await c.post(f"{API}/mentor/chat", json={"message": f"m{i}"}, headers=_auth())
            assert r.status_code == 200, f"call {i} should pass"
        r = await c.post(f"{API}/mentor/chat", json={"message": "one too many"}, headers=_auth())
    assert r.status_code == 429
    d = r.json()["detail"]
    assert d["error"] == "rate_limited"
    assert "retry_after_seconds" in d


# ── Resume score / rewrite: real sqlite session (exercises the DB-write path) ─
import pytest_asyncio
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models.resume import Resume
from app.llm.cost_tracker import AIUsageLog
import app.api.v1.ai_features as _aif


class FakeResume:
    def __init__(self):
        self.raw_text = "Embedded engineer with 5 years of RTOS and CAN experience."


class FakeJob:
    title = "Senior Firmware Engineer"
    description = "Own RTOS bring-up and CAN stack integration for automotive ECUs."


class FakeResumeAgent:
    def __init__(self, db): ...
    async def score(self, resume_text, job_description, user_id):
        return ResumeScore(score=78, ats_score=70, missing_keywords=["autosar"],
                           strengths=["RTOS"], improvements=["Add metrics"])
    async def rewrite(self, resume_text, job, twin, user_id):
        return RewrittenResume(rewritten_bullets=["Led RTOS bring-up", "Integrated CAN stack"],
                               summary="Automotive firmware engineer.",
                               keywords_added=["autosar"], estimated_score_improvement=15)


@pytest_asyncio.fixture
async def sqlite_override():
    """Bind get_db to a shared in-memory sqlite session (resumes + usage tables)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Resume.__table__.create)
        await conn.run_sync(AIUsageLog.__table__.create)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with Session() as s:
            yield s
            await s.commit()

    app.dependency_overrides[db_session.get_db] = _override
    yield Session
    await engine.dispose()


@pytest.mark.asyncio
async def test_resume_score_success(monkeypatch, sqlite_override):
    monkeypatch.setattr(_aif.ResumeRepository, "get_for_user", AsyncMock(return_value=FakeResume()))
    monkeypatch.setattr(_aif.DiscoveredJobRepository, "get_by_id", AsyncMock(return_value=FakeJob()))
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", FakeResumeAgent)
    async with _client() as c:
        r = await c.post(f"{API}/resume/r1/score", json={"job_id": "j1"}, headers=_auth())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["score"] == 78 and d["missing_keywords"] == ["autosar"]


@pytest.mark.asyncio
async def test_resume_score_404_when_missing(monkeypatch, sqlite_override):
    monkeypatch.setattr(_aif.ResumeRepository, "get_for_user", AsyncMock(return_value=None))
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", FakeResumeAgent)
    async with _client() as c:
        r = await c.post(f"{API}/resume/missing/score", json={}, headers=_auth())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_resume_rewrite_requires_job_id(monkeypatch, sqlite_override):
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", FakeResumeAgent)
    async with _client() as c:
        r = await c.post(f"{API}/resume/r1/rewrite", json={}, headers=_auth())
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_resume_rewrite_success_saves_version(monkeypatch, sqlite_override):
    monkeypatch.setattr(_aif.ResumeRepository, "get_for_user", AsyncMock(return_value=FakeResume()))
    monkeypatch.setattr(_aif.DiscoveredJobRepository, "get_by_id", AsyncMock(return_value=FakeJob()))
    monkeypatch.setattr(_aif.CareerTwinRepository, "get_by_user", AsyncMock(return_value=None))
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", FakeResumeAgent)
    async with _client() as c:
        r = await c.post(f"{API}/resume/r1/rewrite", json={"job_id": "j1"}, headers=_auth())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["version_id"]  # real uuid populated after flush
    assert d["score_improvement"] == 15
    assert "CAN stack" in d["preview"]

    # The generated resume version was actually persisted.
    Session = sqlite_override
    from sqlalchemy import select
    async with Session() as s:
        rows = (await s.execute(select(Resume).where(Resume.is_auto_generated == True))).scalars().all()  # noqa: E712
    assert len(rows) == 1
    assert rows[0].generated_for_job_id == "j1"
    assert rows[0].raw_text.startswith("Automotive firmware engineer.")

