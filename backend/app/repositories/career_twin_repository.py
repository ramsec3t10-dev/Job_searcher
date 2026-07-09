"""EMBEDHUNT AI — Career Twin Repository."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.career_twin import CareerTwin
from app.common.base_repository import BaseRepository

_SCORE_FIELDS = {
    "embedded_domain_score",
    "profile_completeness",
    "interview_readiness_score",
    "market_value_score",
    "learning_velocity",
    "avg_interview_score",
}


class CareerTwinRepository(BaseRepository[CareerTwin]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, CareerTwin)

    async def get_by_user(self, user_id: str) -> Optional[CareerTwin]:
        r = await self.db.execute(select(CareerTwin).where(CareerTwin.user_id == user_id))
        return r.scalar_one_or_none()

    async def create_from_resume(self, user_id: str, parsed_resume: dict) -> CareerTwin:
        """Create a twin directly from a parsed-resume dict (data-level).

        Skills are stored expanded; callers pass already-shaped skill dicts or
        plain names which are wrapped with default confidence.
        """
        year = datetime.now(timezone.utc).year
        skills = []
        for entry in parsed_resume.get("skills", []) or []:
            if isinstance(entry, dict):
                skills.append(entry)
            else:
                skills.append({
                    "name": entry, "category": "", "confidence": 0.6, "depth": "working",
                    "years_used": parsed_resume.get("total_years", 0.0), "recency_score": 1.0,
                    "last_used_year": year, "source": "resume",
                })
        contact = parsed_resume.get("contact", {}) or {}
        return await self.create(
            user_id=user_id,
            full_name=contact.get("name", ""),
            email=contact.get("email", ""),
            phone=contact.get("phone", ""),
            skills=skills,
            experience_entries=parsed_resume.get("experience", []) or [],
            education_entries=parsed_resume.get("education", []) or [],
            projects=parsed_resume.get("projects", []) or [],
            certifications=parsed_resume.get("certifications", []) or [],
            total_years_experience=float(parsed_resume.get("total_years", 0.0) or 0.0),
        )

    async def update_skills(self, user_id: str, skills: list[dict]) -> Optional[CareerTwin]:
        twin = await self.get_by_user(user_id)
        if not twin:
            return None
        twin.skills = skills
        await self.db.flush()
        return twin

    async def update_scores(self, user_id: str, scores: dict) -> Optional[CareerTwin]:
        twin = await self.get_by_user(user_id)
        if not twin:
            return None
        for key, value in scores.items():
            if key in _SCORE_FIELDS:
                setattr(twin, key, value)
        await self.db.flush()
        return twin

    async def add_interview_result(self, user_id: str, result: dict) -> Optional[CareerTwin]:
        twin = await self.get_by_user(user_id)
        if not twin:
            return None
        history = list(twin.interview_history or [])
        history.append(result)
        twin.interview_history = history
        await self.db.flush()
        return twin

    async def mark_skill_learned(self, user_id: str, skill_name: str, confidence: float) -> Optional[CareerTwin]:
        twin = await self.get_by_user(user_id)
        if not twin:
            return None
        confidence = max(0.0, min(1.0, confidence))
        year = datetime.now(timezone.utc).year
        skills = [dict(s) for s in (twin.skills or [])]
        for s in skills:
            if s.get("name", "").lower() == skill_name.lower():
                s["confidence"] = max(s.get("confidence", 0.0), confidence)
                s["depth"] = "working"
                s["recency_score"] = 1.0
                s["last_used_year"] = year
                s["source"] = "learned"
                break
        else:
            skills.append({
                "name": skill_name, "category": "", "confidence": confidence, "depth": "working",
                "years_used": 0.0, "recency_score": 1.0, "last_used_year": year, "source": "learned",
            })
        twin.skills = skills
        await self.db.flush()
        return twin

    async def increment_version(self, user_id: str) -> int:
        twin = await self.get_by_user(user_id)
        if not twin:
            return 0
        twin.version = (twin.version or 1) + 1
        await self.db.flush()
        return twin.version

    async def get_skills_list(self, user_id: str) -> list[str]:
        twin = await self.get_by_user(user_id)
        if not twin:
            return []
        return [s.get("name", "") for s in (twin.skills or []) if s.get("name")]
