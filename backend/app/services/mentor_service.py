"""EMBEDHUNT AI — Career Mentor Service (Module 15)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.mentor.career_mentor import CareerMentorEngine
from app.services.career_twin_service import CareerTwinService

logger = get_logger(__name__)


class MentorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_svc = CareerTwinService(db)
        self.engine = CareerMentorEngine()

    async def chat(self, user_id: str, message: str, history: list[dict] | None = None) -> dict:
        context = await self._build_context(user_id)
        result = await self.engine.answer(message, context, history)
        logger.info("mentor_chat", user_id=user_id, source=result["source"])
        return result

    async def _build_context(self, user_id: str) -> dict:
        try:
            summary = await self.twin_svc.get_twin_summary(user_id)
            twin = await self.twin_svc.get_twin(user_id)
        except Exception:  # noqa: BLE001 — mentor works even without a twin
            return {"full_name": "", "note": "Career Twin not initialized."}
        return {
            "full_name": summary.get("full_name"),
            "current_role": summary.get("current_role"),
            "career_level": summary.get("career_level"),
            "total_years_experience": summary.get("total_years_experience"),
            "top_skills": summary.get("top_skills"),
            "interview_readiness_score": summary.get("interview_readiness_score"),
            "market_value_score": summary.get("market_value_score"),
            "embedded_domain_score": summary.get("embedded_domain_score"),
            "dream_companies": summary.get("dream_companies"),
            "known_weaknesses": list(twin.known_weaknesses or []),
            "strengths": list(twin.strengths or []),
        }
