"""EMBEDHUNT AI — Roadmap Service"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.recommendation_service import RecommendationService
from app.services.profile_service import ProfileService
from app.roadmap.planner import generate_roadmap, LearningRoadmap
from app.recommendation.engine import run_matching
from dataclasses import asdict

class RoadmapService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_svc = ProfileService(db)

    @staticmethod
    def _domain_of(job) -> str | None:
        from app.domains.catalog import code_for_domain_id
        return code_for_domain_id(getattr(job, "domain_id", None))

    async def get_roadmap_for_job(self, user_id: str, job_id: str) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        result = run_matching(profile, min_score=0, salary_min=0)
        job = next((j for j in result.jobs if j.job_id == job_id), None)
        if not job: raise HTTPException(404, f"Job {job_id} not found")
        roadmap = generate_roadmap(user_id, job.match.missing_skills, job.match_score,
                                   job.title, domain_code=self._domain_of(job))
        return self._serialize(roadmap)

    async def get_general_roadmap(self, user_id: str) -> dict:
        """Roadmap based on top-3 matched jobs' combined gaps."""
        profile = await self.profile_svc.get_candidate_profile(user_id)
        result = run_matching(profile, min_score=40, salary_min=0)
        if not result.jobs: return {"message": "No matched jobs found. Upload your resume first."}
        top3 = result.jobs[:3]
        all_missing = list(dict.fromkeys(skill for j in top3 for skill in j.match.missing_skills))
        avg_score = int(sum(j.match_score for j in top3) / len(top3))
        roadmap = generate_roadmap(user_id, all_missing, avg_score, "Top Matched Roles",
                                   domain_code=self._domain_of(top3[0]))
        return self._serialize(roadmap)

    def _serialize(self, r: LearningRoadmap) -> dict:
        return {
            "job_title": r.job_title, "current_score": r.current_score,
            "projected_score": r.projected_score, "total_hours": r.total_hours,
            "total_weeks": r.total_weeks, "summary": r.summary,
            "immediate_actions": r.immediate_actions,
            "tasks": [
                {"skill": t.skill, "priority": t.priority, "level": t.level.value,
                 "estimated_hours": t.estimated_hours, "weeks_estimate": t.weeks_estimate,
                 "status": t.status.value, "resources": t.resources}
                for t in r.tasks
            ],
        }
