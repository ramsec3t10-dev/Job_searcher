"""EMBEDHUNT AI — Mock interview service (engine + persistence + twin feedback)."""
from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interview_engine import InterviewEngine, get_interview_engine
from app.models.interview import InterviewSession
from app.repositories.career_twin_repository import CareerTwinRepository
from app.services.career_twin_service import CareerTwinService


class MockInterviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine: InterviewEngine = get_interview_engine()
        self.twin_repo = CareerTwinRepository(db)

    async def generate(self, user_id: str, *, skills: list[str] | None = None,
                       count: int = 10, company: str = "", job_title: str = "Mock Interview",
                       fmt: str = "adaptive") -> dict:
        twin = await self.twin_repo.get_by_user(user_id)
        weak: list[str] = []
        if skills is None:
            if twin is None:
                raise HTTPException(404, "Career Twin not initialized; pass skills explicitly.")
            skills = [s.get("name", "") for s in (twin.skills or []) if s.get("name")]
        if twin is not None:
            weak = list(twin.known_weaknesses or [])
            weak += [s.get("name", "") for s in (twin.skills or [])
                     if 0 < float(s.get("confidence", 0.0)) < 0.5]

        stages: list[dict] = []
        if fmt == "realistic":
            # Full interview arc: intro → warm-up → deep-dive → coding →
            # behavioral → your-questions. Same flat list feeds evaluate().
            built = self.engine.build_realistic_session(skills, weak_skills=weak)
            questions = built["questions"]
            stages = built["stages"]
        else:
            questions = self.engine.build_session(skills, count=count, weak_skills=weak)
        q_dicts = [q.to_dict() for q in questions]

        session = InterviewSession(
            user_id=user_id, job_title=job_title, company=company or None,
            questions_json=json.dumps([q.to_dict(include_expected=True) for q in questions]),
            estimated_prep_days=max(3, len(questions)),
        )
        self.db.add(session)
        await self.db.flush()
        result = {
            "session_id": session.id,
            "job_title": job_title,
            "company": company,
            "format": fmt,
            "focus_weak_skills": sorted(set(weak)),
            "total_questions": len(q_dicts),
            "questions": q_dicts,
        }
        if stages:
            result["stages"] = stages
        return result

    async def evaluate(self, user_id: str, session_id: str, answers: dict[str, str],
                       *, feed_twin: bool = True) -> dict:
        session = await self._get_session(session_id, user_id)
        stored = json.loads(session.questions_json or "[]")
        total = len(stored) or len(answers)
        evaluation = self.engine.evaluate(answers, total=total)

        session.readiness_score = evaluation.readiness_score
        session.is_completed = True
        await self.db.flush()

        if feed_twin:
            twin = await self.twin_repo.get_by_user(user_id)
            if twin is not None:
                await CareerTwinService(self.db).add_interview_result(user_id, {
                    "company": session.company or "",
                    "role": session.job_title,
                    "outcome": "mock",
                    "weak_topics": evaluation.weak_skills,
                    "strong_topics": evaluation.strong_skills,
                    "notes": f"Mock interview readiness {evaluation.readiness_score}/100",
                })
        out = evaluation.to_dict()
        out["session_id"] = session_id
        return out

    async def _get_session(self, session_id: str, user_id: str) -> InterviewSession:
        session = await self.db.get(InterviewSession, session_id)
        if session is None or session.user_id != user_id:
            raise HTTPException(404, "Interview session not found")
        return session
