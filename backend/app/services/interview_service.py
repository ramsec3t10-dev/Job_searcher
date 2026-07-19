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
        from app.domains.catalog import code_for_domain_id
        kit = await generate_interview_kit_ai(job.title, job.company, job.match.matched_skills, job.match_score, db=self.db, user_id=user_id, domain_code=code_for_domain_id(getattr(job, "domain_id", None)))
        resp = {
            "job_title": kit.job_title, "company": kit.company,
            "readiness_score": kit.readiness_score,
            "preparation_summary": kit.preparation_summary,
            "focus_skills": kit.focus_skills,
            "total_questions": kit.total_questions,
            "questions_by_skill": kit.questions_by_skill,
            "coding_topics": kit.coding_topics,
            "checklist": kit.checklist,
        }
        # Phase 7: overlay curated bank questions for this subrole when they
        # exist; otherwise the AI kit above stands alone (critical fallback).
        resp.update(await self._curated_overlay(job))
        return resp

    async def _curated_overlay(self, job) -> dict:
        """Attach curated questions for the job's inferred subrole. Returns
        ``question_source='curated'`` + grouped questions when the bank has any,
        else ``question_source='generated'`` with an empty list."""
        from app.interview.subrole import infer_subrole
        from app.repositories.interview_bank_repository import InterviewBankRepository
        subrole = infer_subrole(job.title)
        curated: list = []
        if subrole:
            try:
                rows = await InterviewBankRepository(self.db).get_by_subrole(subrole, limit=30)
                curated = [
                    {"question_text": q.question_text, "category": q.category.value,
                     "difficulty": q.difficulty.value,
                     "model_answer_guideline": q.model_answer_guideline}
                    for q in rows
                ]
            except Exception:  # noqa: BLE001 — bank is optional, never break prep
                curated = []
        return {
            "subrole": subrole,
            "question_source": "curated" if curated else "generated",
            "curated_questions": curated,
        }

    async def get_general_prep(self, user_id: str) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        if not profile.all_skills:
            return {"message": "Upload and process your resume first to get interview preparation."}
        result = run_matching(profile, min_score=40, salary_min=0)
        if not result.jobs:
            return {"message": "No matched jobs found. Upload resume first."}
        top_job = result.jobs[0]
        from app.domains.catalog import code_for_domain_id
        kit = await generate_interview_kit_ai(top_job.title, top_job.company, top_job.match.matched_skills, top_job.match_score, db=self.db, user_id=user_id, domain_code=code_for_domain_id(getattr(top_job, "domain_id", None)))
        return {
            "based_on": f"{top_job.title} at {top_job.company}",
            "readiness_score": kit.readiness_score,
            "preparation_summary": kit.preparation_summary,
            "focus_skills": kit.focus_skills,
            "questions_by_skill": kit.questions_by_skill,
            "coding_topics": kit.coding_topics,
            "checklist": kit.checklist,
        }
