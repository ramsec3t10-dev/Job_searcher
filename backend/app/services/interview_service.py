"""EMBEDHUNT AI — Interview Service"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.profile_service import ProfileService
from app.recommendation.engine import run_matching
from app.interview.generator import generate_interview_kit_ai

class InterviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_svc = ProfileService(db)

    async def get_interview_kit(self, user_id: str, job_id: str) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        result = run_matching(profile, min_score=0, salary_min=0)
        job = next((j for j in result.jobs if j.job_id == job_id), None)
        if not job: raise HTTPException(404, f"Job {job_id} not found")
        kit = await generate_interview_kit_ai(job.title, job.company, job.match.matched_skills, job.match_score, db=self.db, user_id=user_id)
        return {
            "job_title": kit.job_title, "company": kit.company,
            "readiness_score": kit.readiness_score,
            "preparation_summary": kit.preparation_summary,
            "focus_skills": kit.focus_skills,
            "total_questions": kit.total_questions,
            "questions_by_skill": kit.questions_by_skill,
            "coding_topics": kit.coding_topics,
            "checklist": kit.checklist,
        }

    async def get_general_prep(self, user_id: str) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        if not profile.all_skills:
            return {"message": "Upload and process your resume first to get interview preparation."}
        result = run_matching(profile, min_score=40, salary_min=0)
        if not result.jobs:
            return {"message": "No matched jobs found. Upload resume first."}
        top_job = result.jobs[0]
        kit = await generate_interview_kit_ai(top_job.title, top_job.company, top_job.match.matched_skills, top_job.match_score, db=self.db, user_id=user_id)
        return {
            "based_on": f"{top_job.title} at {top_job.company}",
            "readiness_score": kit.readiness_score,
            "preparation_summary": kit.preparation_summary,
            "focus_skills": kit.focus_skills,
            "questions_by_skill": kit.questions_by_skill,
            "coding_topics": kit.coding_topics,
            "checklist": kit.checklist,
        }
