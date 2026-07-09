"""EMBEDHUNT AI — Adaptive roadmap service (CareerTwin-driven)."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adaptive_roadmap import AdaptiveRoadmapEngine, get_adaptive_engine
from app.company.profiles import get_profile
from app.repositories.career_twin_repository import CareerTwinRepository
from app.services.feedback_service import FeedbackService

_CONFIDENT = 0.6


class AdaptiveRoadmapService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_repo = CareerTwinRepository(db)
        self.feedback = FeedbackService(db)
        self.engine: AdaptiveRoadmapEngine = get_adaptive_engine()

    async def _twin_confidence(self, user_id: str):
        twin = await self.twin_repo.get_by_user(user_id)
        if twin is None:
            raise HTTPException(404, "Career Twin not initialized.")
        conf = {s.get("name", "").lower(): float(s.get("confidence", 0.0)) for s in (twin.skills or [])}
        return conf, twin

    async def roadmap_for_targets(self, user_id: str, target_skills: list[str],
                                  job_title: str = "Target Role",
                                  hours_per_week: int = 10,
                                  demand: dict[str, int] | None = None) -> dict:
        conf, _ = await self._twin_confidence(user_id)
        affinities = (await self.feedback.get_affinities(user_id)).get("skill_affinity", {})
        current_score = self._coverage_score(conf, target_skills)
        roadmap = await self.engine.build_ai(
            skill_confidence=conf, target_skills=target_skills,
            current_score=current_score, job_title=job_title,
            db=self.db, user_id=user_id,
            affinities=affinities, demand=demand, hours_per_week=hours_per_week,
        )
        return roadmap.to_dict()

    async def roadmap_for_dream_companies(self, user_id: str, hours_per_week: int = 10) -> dict:
        conf, twin = await self._twin_confidence(user_id)
        dream = list(twin.dream_companies or [])
        if not dream:
            raise HTTPException(409, "No dream companies set on the Career Twin.")
        demand: dict[str, int] = {}
        for name in dream:
            profile = get_profile(name)
            if not profile:
                continue
            for skill in profile.tech_stack:
                demand[skill.lower()] = demand.get(skill.lower(), 0) + 1
        if not demand:
            raise HTTPException(409, "Dream companies are not in the intelligence database.")
        target_skills = list(demand.keys())
        affinities = (await self.feedback.get_affinities(user_id)).get("skill_affinity", {})
        current_score = self._coverage_score(conf, target_skills)
        roadmap = await self.engine.build_ai(
            skill_confidence=conf, target_skills=target_skills,
            current_score=current_score, job_title="Dream Companies",
            db=self.db, user_id=user_id,
            affinities=affinities, demand=demand, hours_per_week=hours_per_week,
        )
        out = roadmap.to_dict()
        out["dream_companies"] = dream
        return out

    @staticmethod
    def _coverage_score(conf: dict[str, float], targets: list[str]) -> int:
        targets = list(dict.fromkeys(t.lower() for t in targets))
        if not targets:
            return 0
        have = sum(1 for t in targets if conf.get(t, 0.0) >= _CONFIDENT)
        return int(round(have / len(targets) * 100))
