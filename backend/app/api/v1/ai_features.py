"""EMBEDHUNT AI — AI Agent feature endpoints (Phase 6).

Exposes the full AI agent layer (mentor, resume, interview, learning, salary,
coding, cost) to the mobile app. All routes are additive and namespaced under
``/ai``. Every AI-calling route passes through :func:`ai_guard`, which enforces
the global enrichment toggle and the per-user monthly budget, and raises
:class:`AIUnavailableError` so failures return one consistent JSON envelope.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id, require_role, UserRole
from app.api.v1.rate_limit import rate_limit
from app.config.logging import get_logger
from app.config.settings import settings
from app.database.session import get_db
from app.llm.cost_tracker import AIUsageLog, CostTracker
from app.models.resume import Resume, ResumeStatus
from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.discovered_job_repository import DiscoveredJobRepository
from app.repositories.resume_repository import ResumeRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Features"])

_MAX_CODE_BYTES = 50_000


# ── Consistent error envelope ────────────────────────────────────────────────
class AIUnavailableError(Exception):
    """Raised by AI routes/guard; rendered by the handler in ``app.main``."""

    def __init__(self, status_code: int, error: str, message: str,
                 fallback_available: bool = True):
        self.status_code = status_code
        self.error = error
        self.message = message
        self.fallback_available = fallback_available
        super().__init__(message)


# ── Guard: budget + master toggle (also supplies the authenticated user id) ──
async def ai_guard(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> str:
    if not settings.LLM_ENRICHMENT_ENABLED:
        raise AIUnavailableError(
            503, "ai_disabled",
            "AI features are currently disabled. Please try again later.",
            fallback_available=True,
        )
    if await CostTracker().is_over_budget(user_id, db=db):
        raise AIUnavailableError(
            429, "budget_exceeded",
            "Monthly AI budget reached. Access resets at the start of next cycle.",
            fallback_available=False,
        )
    return user_id


# ── In-process rate limiting + short-lived caches ────────────────────────────
class _RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max = max_calls
        self.window = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        recent = [t for t in self._hits.get(key, []) if now - t < self.window]
        if len(recent) >= self.max:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        return True


class _TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[dict, float]] = {}

    def get(self, key: str) -> Optional[dict]:
        item = self._store.get(key)
        if not item:
            return None
        value, ts = item
        if time.monotonic() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: dict) -> None:
        self._store[key] = (value, time.monotonic())


_mentor_limiter = _RateLimiter(max_calls=20, window_seconds=3600)  # 20/hour per user
_brief_cache = _TTLCache(ttl_seconds=30 * 60)                      # 30 min per user
_salary_cache = _TTLCache(ttl_seconds=24 * 3600)                   # 24 h per user


# ── Helpers ──────────────────────────────────────────────────────────────────
async def _run(coro):
    """Await an agent call, mapping any failure to the consistent AI envelope."""
    try:
        return await coro
    except AIUnavailableError:
        raise
    except Exception as e:  # noqa: BLE001 — surface a uniform error to the client
        logger.warning("ai_endpoint_failed", error=str(e))
        raise AIUnavailableError(
            503, "ai_unavailable",
            "AI feature temporarily unavailable. Try again in 30 seconds.",
            fallback_available=True,
        )


async def _latest_tokens(db: AsyncSession, user_id: str) -> int:
    """Tokens consumed by the user's most recent AI call (0 if none logged)."""
    stmt = (
        select(AIUsageLog.tokens_in, AIUsageLog.tokens_out)
        .where(AIUsageLog.user_id == user_id)
        .order_by(AIUsageLog.created_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return 0
    return int((row[0] or 0) + (row[1] or 0))


# ── MENTOR ───────────────────────────────────────────────────────────────────
@router.post(
    "/mentor/chat",
    summary="Chat with the AI Career Mentor",
    dependencies=[Depends(rate_limit("mentor_chat", 20, 3600))],
)
async def mentor_chat(
    payload: dict = Body(..., example={"message": "How do I get into Qualcomm?", "conversation_id": ""}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(422, "Field 'message' is required.")
    if not _mentor_limiter.allow(user_id):
        raise AIUnavailableError(
            429, "rate_limited",
            "Rate limit reached: 20 mentor messages per hour. Try again later.",
            fallback_available=False,
        )
    conversation_id = (payload.get("conversation_id") or "").strip() or str(uuid.uuid4())

    from app.agents.mentor_agent import MentorAgent

    result = await _run(MentorAgent(db).advise(user_id, message, conversation_id))
    return {
        "reply": result.advice,
        "action_items": result.action_items,
        "conversation_id": conversation_id,
        "tokens_used": await _latest_tokens(db, user_id),
    }


@router.get("/mentor/daily-brief", summary="Personalised daily brief (cached 30 min)")
async def mentor_daily_brief(
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    cached = _brief_cache.get(user_id)
    if cached is not None:
        return cached

    from app.agents.mentor_agent import MentorAgent

    brief = await _run(MentorAgent(db).daily_brief(user_id))
    data = brief.model_dump()
    _brief_cache.set(user_id, data)
    return data


# ── RESUME ───────────────────────────────────────────────────────────────────
@router.post(
    "/resume/{resume_id}/score",
    summary="Score a resume (optionally vs a job)",
    dependencies=[Depends(rate_limit("resume_score", 10, 3600))],
)
async def resume_score(
    resume_id: str,
    payload: dict = Body(default={}, example={"job_id": ""}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    resume = await ResumeRepository(db).get_for_user(resume_id, user_id)
    if not resume or not resume.raw_text:
        raise HTTPException(404, "Resume not found or not yet processed.")

    job_description = ""
    job_id = (payload.get("job_id") or "").strip()
    if job_id:
        job = await DiscoveredJobRepository(db).get_by_id(job_id)
        if job:
            job_description = job.description or job.title or ""

    from app.agents.resume_agent import ResumeAgent

    result = await _run(ResumeAgent(db).score(resume.raw_text, job_description, user_id))
    return result.model_dump()


@router.post(
    "/resume/{resume_id}/rewrite",
    summary="Rewrite a resume for a job (saves a version)",
    dependencies=[Depends(rate_limit("resume_rewrite", 5, 3600))],
)
async def resume_rewrite(
    resume_id: str,
    payload: dict = Body(..., example={"job_id": "job-123"}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    job_id = (payload.get("job_id") or "").strip()
    if not job_id:
        raise HTTPException(422, "Field 'job_id' is required.")

    resume = await ResumeRepository(db).get_for_user(resume_id, user_id)
    if not resume or not resume.raw_text:
        raise HTTPException(404, "Resume not found or not yet processed.")

    job = await DiscoveredJobRepository(db).get_by_id(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found.")

    twin = await CareerTwinRepository(db).get_by_user(user_id)
    job_dict = {"title": job.title or "", "description": job.description or ""}

    from app.agents.resume_agent import ResumeAgent

    result = await _run(ResumeAgent(db).rewrite(resume.raw_text, job_dict, twin, user_id))

    rewritten_text = "\n".join(
        part for part in [
            result.summary,
            "\n".join(f"• {b}" for b in result.rewritten_bullets),
        ] if part
    ).strip()

    version = Resume(
        user_id=user_id,
        name=f"Tailored: {(job.title or 'Job')[:150]}",
        file_url="generated://ai-rewrite",
        file_name=f"tailored_{job_id}.txt",
        file_type="txt",
        status=ResumeStatus.PARSED,
        raw_text=rewritten_text,
        is_auto_generated=True,
        generated_for_job_id=job_id,
    )
    db.add(version)
    await db.flush()

    return {
        "version_id": version.id,
        "score_improvement": result.estimated_score_improvement,
        "preview": rewritten_text[:500],
    }


# ── INTERVIEW ────────────────────────────────────────────────────────────────
@router.post("/interview/questions", summary="Generate tailored interview questions")
async def interview_questions(
    payload: dict = Body(..., example={"skill": "rtos", "company": "Bosch", "difficulty": "medium", "count": 5}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    skill = (payload.get("skill") or "").strip()
    if not skill:
        raise HTTPException(422, "Field 'skill' is required.")
    company = (payload.get("company") or "").strip()
    difficulty = (payload.get("difficulty") or "medium").strip()
    count = int(payload.get("count", 5) or 5)

    from app.agents.interview_agent import InterviewAgent

    questions = await _run(
        InterviewAgent(db).generate_questions(user_id, skill, company, difficulty, count)
    )
    return {"questions": [q.model_dump() for q in questions]}


@router.post(
    "/interview/evaluate",
    summary="Evaluate an interview answer",
    dependencies=[Depends(rate_limit("interview_evaluate", 30, 3600))],
)
async def interview_evaluate(
    payload: dict = Body(..., example={"question": "What is priority inversion?", "answer": "...", "skill": "rtos"}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    question = (payload.get("question") or "").strip()
    answer = (payload.get("answer") or "").strip()
    skill = (payload.get("skill") or "").strip()
    if not question or not answer:
        raise HTTPException(422, "Fields 'question' and 'answer' are required.")

    from app.agents.interview_agent import InterviewAgent

    result = await _run(InterviewAgent(db).evaluate_answer(user_id, question, answer, skill))
    return result.model_dump()


# ── LEARNING ─────────────────────────────────────────────────────────────────
@router.post("/learn/lesson", summary="Generate a bite-sized lesson")
async def learn_lesson(
    payload: dict = Body(..., example={"skill": "can", "topic": "CAN arbitration"}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    skill = (payload.get("skill") or "").strip()
    topic = (payload.get("topic") or "").strip()
    if not skill or not topic:
        raise HTTPException(422, "Fields 'skill' and 'topic' are required.")

    from app.agents.learning_agent import LearningAgent

    result = await _run(LearningAgent(db).create_lesson(user_id, skill, topic))
    return result.model_dump()


@router.post("/learn/flashcards", summary="Generate spaced-repetition flashcards")
async def learn_flashcards(
    payload: dict = Body(..., example={"skill": "rtos"}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    skill = (payload.get("skill") or "").strip()
    if not skill:
        raise HTTPException(422, "Field 'skill' is required.")

    from app.agents.learning_agent import LearningAgent

    cards = await _run(LearningAgent(db).create_flashcards(user_id, skill))
    return {"cards": [c.model_dump() for c in cards]}


# ── SALARY ───────────────────────────────────────────────────────────────────
@router.get("/salary/estimate", summary="AI salary estimate (cached 24 h)")
async def salary_estimate(
    company: Optional[str] = Query(default=None),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    key = f"{user_id}:{(company or '').strip().lower()}"
    cached = _salary_cache.get(key)
    if cached is not None:
        return cached

    from app.agents.salary_agent import SalaryAgent

    result = await _run(SalaryAgent(db).estimate(user_id, company or None))
    data = result.model_dump()
    _salary_cache.set(key, data)
    return data


# ── CODING ───────────────────────────────────────────────────────────────────
@router.post(
    "/code/review",
    summary="AI review of embedded C/C++",
    dependencies=[Depends(rate_limit("code_review", 15, 3600))],
)
async def code_review(
    payload: dict = Body(..., example={"code": "void isr(){ x=1; }", "language": "c"}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    code = payload.get("code") or ""
    language = (payload.get("language") or "c").strip().lower()
    if not code.strip():
        raise HTTPException(422, "Field 'code' is required and cannot be empty.")
    if len(code.encode("utf-8")) > _MAX_CODE_BYTES:
        raise HTTPException(413, "Code exceeds the 50 KB review limit.")

    from app.agents.coding_agent import CodingAgent

    result = await _run(CodingAgent(db).review_code(user_id, code, language))
    return result.model_dump()


@router.post("/code/challenge", summary="Generate a coding challenge")
async def code_challenge(
    payload: dict = Body(..., example={"skill": "c", "difficulty": "medium"}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    skill = (payload.get("skill") or "").strip()
    if not skill:
        raise HTTPException(422, "Field 'skill' is required.")
    difficulty = (payload.get("difficulty") or "medium").strip()

    from app.agents.coding_agent import CodingAgent

    result = await _run(CodingAgent(db).generate_challenge(user_id, skill, difficulty))
    return result.model_dump()


# ── COST / USAGE (not budget-gated: users must always see their usage) ───────
@router.get("/usage", summary="This month's AI usage and remaining budget")
async def ai_usage(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = (
        select(
            AIUsageLog.task_type,
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0.0),
            func.count(),
        )
        .where(AIUsageLog.user_id == user_id, AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.task_type)
    )
    rows = (await db.execute(stmt)).all()

    breakdown: dict[str, dict] = {}
    total_cost = 0.0
    total_calls = 0
    for task_type, cost, calls in rows:
        breakdown[task_type] = {"cost_usd": round(float(cost), 6), "calls": int(calls)}
        total_cost += float(cost)
        total_calls += int(calls)

    limit = settings.LLM_MAX_MONTHLY_COST_USD
    return {
        "this_month_usd": round(total_cost, 6),
        "this_month_calls": total_calls,
        "budget_remaining_usd": round(max(0.0, limit - total_cost), 6),
        "breakdown_by_task": breakdown,
    }


# ── OBSERVABILITY ────────────────────────────────────────────────────────────
@router.get(
    "/system/health",
    summary="AI system health (admin only)",
    dependencies=[Depends(require_role(UserRole.PLATFORM_ADMIN))],
)
async def ai_system_health(db: AsyncSession = Depends(get_db)):
    from app.services.ai_analytics_service import AIAnalyticsService

    return await AIAnalyticsService(db).get_system_health()


@router.get("/insights", summary="Your personal AI usage and learning insights")
async def ai_insights(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_analytics_service import AIAnalyticsService

    return await AIAnalyticsService(db).get_user_insights(user_id)


# ── STREAMING (bonus): SSE mentor chat ───────────────────────────────────────
@router.post(
    "/mentor/chat/stream",
    summary="Streaming (SSE) AI Career Mentor chat",
    dependencies=[Depends(rate_limit("mentor_chat", 20, 3600))],
)
async def mentor_chat_stream(
    payload: dict = Body(..., example={"message": "How do I get into Qualcomm?", "conversation_id": ""}),
    user_id: str = Depends(ai_guard),
    db: AsyncSession = Depends(get_db),
):
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(422, "Field 'message' is required.")
    if not _mentor_limiter.allow(user_id):
        raise AIUnavailableError(
            429, "rate_limited",
            "Rate limit reached: 20 mentor messages per hour. Try again later.",
            fallback_available=False,
        )
    conversation_id = (payload.get("conversation_id") or "").strip() or str(uuid.uuid4())

    async def event_stream():
        from app.agents.mentor_agent import MentorAgent

        try:
            result = await MentorAgent(db).advise(user_id, message, conversation_id)
        except Exception as e:  # noqa: BLE001 — stream a uniform error frame
            logger.warning("ai_stream_failed", error=str(e))
            payload_err = {
                "error": "ai_unavailable",
                "message": "AI feature temporarily unavailable. Try again in 30 seconds.",
                "fallback_available": True,
            }
            yield f"data: {json.dumps(payload_err)}\n\n"
            return

        text = result.advice or ""
        for i in range(0, len(text), 40):
            yield f'data: {json.dumps({"delta": text[i:i + 40]})}\n\n'
        tokens = await _latest_tokens(db, user_id)
        yield f'data: {json.dumps({"done": True, "conversation_id": conversation_id, "tokens_used": tokens})}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")
