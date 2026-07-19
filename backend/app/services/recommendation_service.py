"""EMBEDHUNT AI — Recommendation Service"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from app.services.profile_service import ProfileService
from app.recommendation.engine import run_matching
from app.recommendation.ranking import RankedJob, RankingResult
from app.repositories.application_repository import ApplicationRepository
from app.models.application import Application, ApplicationStatus, ApplicationOutcome
from app.config.logging import get_logger

logger = get_logger(__name__)

class RecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_svc = ProfileService(db)
        self.app_repo = ApplicationRepository(db)
        self._scoring_cache = None

    async def _scoring_context(self, user_id: str):
        """Load the domain-aware scoring registry (cached per request) and the
        candidate's declared target domain codes. Fails soft to (None, None) so
        matching always works even if the taxonomy isn't seeded."""
        if self._scoring_cache is None:
            try:
                from app.recommendation.scoring_config import load_scoring_configs
                self._scoring_cache = await load_scoring_configs(self.db)
            except Exception as exc:  # noqa: BLE001
                logger.warning("scoring_config_load_failed", error=str(exc))
                self._scoring_cache = {}
        targets: set[str] = set()
        try:
            from sqlalchemy import select as _select
            from app.domains.catalog import code_for_domain_id
            from app.models.profile import CandidateProfile
            row = (await self.db.execute(_select(CandidateProfile).where(
                CandidateProfile.user_id == user_id))).scalar_one_or_none()
            if row:
                for did in [row.primary_domain_id, *(row.secondary_domain_ids or [])]:
                    code = code_for_domain_id(did)
                    if code:
                        targets.add(code)
        except Exception:  # noqa: BLE001
            pass
        return (self._scoring_cache or None), (targets or None)

    async def _apply_learned_boost(self, user_id: str, result) -> None:
        """The learning loop, v1: every swipe/save/apply the user made becomes
        a bounded per-user boost. Company affinity ±3, skill affinity up to ±2,
        so learned preference re-orders near-ties without drowning real fit."""
        try:
            from app.services.feedback_service import FeedbackService
            aff = await FeedbackService(self.db).get_affinities(user_id)
        except Exception:
            return
        skill_aff = aff.get("skills") or aff.get("skill_affinity") or {}
        company_aff = aff.get("companies") or aff.get("company_affinity") or {}
        if not skill_aff and not company_aff:
            return
        for job in result.jobs:
            boost = 3.0 * float(company_aff.get(job.company.lower(), 0.0))
            skills = [s.lower() for s in job.match.matched_skills[:6]]
            if skills:
                boost += 2.0 * (
                    sum(float(skill_aff.get(s, 0.0)) for s in skills) / len(skills))
            job.match_score = int(max(0, min(99, job.match_score + round(boost))))
        result.jobs.sort(key=lambda j: j.match_score, reverse=True)

    async def get_recommendations(self, user_id: str, min_score: int = 40, salary_min: float = 15.0) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        scoring, targets = await self._scoring_context(user_id)
        result = run_matching(profile, min_score, salary_min, scoring=scoring, target_domains=targets)
        await self._apply_learned_boost(user_id, result)
        logger.info("recommendations_generated", user_id=user_id, qualified=result.total_qualified, auto=result.auto_apply_count)
        return self._serialize_result(result)

    async def get_job_gaps(self, user_id: str, job_id: str) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        scoring, targets = await self._scoring_context(user_id)
        result = run_matching(profile, min_score=0, salary_min=0, scoring=scoring, target_domains=targets)
        job = next((j for j in result.jobs if j.job_id == job_id), None)
        if not job: raise HTTPException(404, f"Job {job_id} not found")
        g = job.gap
        return {
            "job_title": g.job_title, "total_score": g.total_score,
            "recommendation": g.recommendation,
            "high_priority": [{"skill": x.skill, "priority": x.priority.value, "resources": x.learning_resources, "in_required": x.in_required} for x in g.high],
            "medium_priority": [{"skill": x.skill, "priority": x.priority.value, "resources": x.learning_resources, "in_required": x.in_required} for x in g.medium],
            "low_priority": [{"skill": x.skill, "priority": x.priority.value, "resources": x.learning_resources} for x in g.low],
            "matched_skills": g.matched_skills,
            "immediate_focus": g.immediate_focus,
            "upskill_weeks": g.upskill_weeks,
            "summary": g.summary,
        }

    async def approve_apply(self, user_id: str, job_id: str, resume_id: str | None = None) -> Application:
        from app.repositories.resume_repository import ResumeRepository
        resume = await ResumeRepository(self.db).get_primary(user_id)
        profile = await self.profile_svc.get_candidate_profile(user_id)
        scoring, targets = await self._scoring_context(user_id)
        result = run_matching(profile, min_score=0, salary_min=0, scoring=scoring, target_domains=targets)
        job = next((j for j in result.jobs if j.job_id == job_id), None)
        if not job: raise HTTPException(404, f"Job {job_id} not found in corpus")
        from app.recommendation.matcher import compute_match
        match = job.match
        app = await self.app_repo.create(
            user_id=user_id, job_id=job_id,
            resume_id=resume.id if resume else (resume_id or ""),
            job_title=job.title, company_name=job.company,
            company_tier=job.company_tier, location=job.location,
            apply_url=job.apply_url or job.source_url,
            source_portal=job.source_portal,
            salary_min_lpa=job.salary_min_lpa,
            salary_max_lpa=job.salary_max_lpa,
            match_score=match.total_score,
            matched_skills=", ".join(match.matched_skills),
            missing_skills=", ".join(match.missing_skills),
            ai_explanation=match.explanation,
            resume_version_name=resume.name if resume else "",
            status=ApplicationStatus.QUEUED,
            outcome=ApplicationOutcome.PENDING,
            approved_at=datetime.now(timezone.utc).isoformat(),
        )
        from app.services.notification_service import NotificationService
        await NotificationService(self.db).create_application_update(
            user_id, job.title, ApplicationStatus.QUEUED.value
        )
        logger.info("application_queued", user_id=user_id, job=job.title, score=match.total_score)
        return app

    def _serialize_result(self, result: RankingResult) -> dict:
        return {
            "candidate": result.candidate,
            "total_scanned": result.total_scanned,
            "total_qualified": result.total_qualified,
            "auto_apply_count": result.auto_apply_count,
            "strong_count": result.strong_count,
            "salary_filter": result.salary_filter,
            "summary": result.summary,
            "jobs": [self._serialize_job(j) for j in result.jobs],
        }

    def _serialize_job(self, j: RankedJob) -> dict:
        from app.domains.catalog import code_for_domain_id, flatten
        dcode = code_for_domain_id(getattr(j, "domain_id", None))
        dname = next((d.name for d in flatten() if d.code == dcode), None) if dcode else None
        return {
            "rank": j.rank, "job_id": j.job_id, "title": j.title,
            "company": j.company, "company_tier": j.company_tier,
            "location": j.location, "source_portal": j.source_portal,
            "source_url": j.source_url, "apply_url": j.apply_url,
            "domain_code": dcode, "domain_name": dname,
            "salary_min_lpa": j.salary_min_lpa, "salary_max_lpa": j.salary_max_lpa,
            "meets_salary": j.meets_salary,
            "match_score": j.match_score, "match_tier": j.match_tier.value,
            "is_auto_apply": j.is_auto_apply,
            "matched_skills": j.match.matched_skills,
            "missing_skills": j.match.missing_skills,
            "explanation": j.match.explanation,
            "recommendation": j.match.recommendation,
            "category_breakdown": [
                {"category": c.category, "weight": c.weight, "matched": c.matched_skills,
                 "job_required": c.job_skills, "raw_score": c.raw_score, "weighted_score": c.weighted_score}
                for c in j.match.category_scores
            ],
        }
