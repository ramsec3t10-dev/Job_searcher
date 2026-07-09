"""EMBEDHUNT AI — Career Twin Service.

The CareerTwin is the single source of truth. The resume parser is used only to
populate it initially; after that every module reads from and writes to the twin.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.models.career_twin import CareerTwin
from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.resume_repository import ResumeRepository
from app.resume.normalizer import CandidateProfile

logger = get_logger(__name__)

_CATEGORY_FIELDS = [
    ("programming_languages", "programming"),
    ("rtos_and_os", "rtos"),
    ("protocols", "protocols"),
    ("hardware_platforms", "hardware"),
    ("automotive_safety", "automotive"),
    ("tools_and_debug", "tools"),
    ("software_concepts", "concepts"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CareerTwinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CareerTwinRepository(db)
        self.resume_repo = ResumeRepository(db)

    # ── Read ──────────────────────────────────────────────────────────────
    async def get_twin(self, user_id: str) -> CareerTwin:
        twin = await self.repo.get_by_user(user_id)
        if not twin:
            raise HTTPException(404, "Career Twin not initialized. Upload a resume and call /career-twin/init.")
        return twin

    async def get_twin_summary(self, user_id: str) -> dict:
        twin = await self.get_twin(user_id)
        top = sorted(twin.skills or [], key=lambda s: s.get("confidence", 0), reverse=True)[:10]
        return {
            "full_name": twin.full_name,
            "current_role": twin.current_role,
            "current_company": twin.current_company,
            "career_level": twin.career_level,
            "total_years_experience": twin.total_years_experience,
            "skill_count": len(twin.skills or []),
            "top_skills": [s["name"] for s in top],
            "embedded_domain_score": twin.embedded_domain_score,
            "profile_completeness": twin.profile_completeness,
            "interview_readiness_score": twin.interview_readiness_score,
            "market_value_score": twin.market_value_score,
            "dream_companies": twin.dream_companies or [],
            "version": twin.version,
            "updated_at": str(twin.updated_at),
        }

    # ── Create ────────────────────────────────────────────────────────────
    async def create_from_resume(self, user_id: str, resume_id: str) -> CareerTwin:
        resume = await self.resume_repo.get_for_user(resume_id, user_id)
        if not resume:
            raise HTTPException(404, "Resume not found")
        if not resume.ai_summary:
            raise HTTPException(409, "Resume not yet processed")
        profile = CandidateProfile.from_json(resume.ai_summary)

        current_year = datetime.now(timezone.utc).year
        skills = self._skills_from_profile(profile, current_year)

        existing = await self.repo.get_by_user(user_id)
        now = _now()
        changed = {k: now for k in ("skills", "identity", "experience", "scores")}
        payload = dict(
            user_id=user_id,
            last_synced_at=now,
            full_name=profile.name_hint or "",
            email=profile.email_hint or "",
            phone=profile.phone_hint or "",
            skills=skills,
            total_years_experience=profile.total_years_experience,
            current_role=profile.current_role or "",
            current_company=profile.current_company or "",
            career_level=self._career_level(profile.total_years_experience),
            education_entries=self._education_from_profile(profile),
            source_resume_id=resume_id,
            last_resume_parse_date=now,
            change_log=changed,
        )
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            existing.version = (existing.version or 1) + 1
            twin = existing
        else:
            twin = await self.repo.create(**payload)

        self._recompute_scores(twin, profile)
        await self.db.flush()
        logger.info("career_twin_created", user_id=user_id, skills=len(skills), version=twin.version)
        return twin

    # ── Update ────────────────────────────────────────────────────────────
    async def update_skill_confidence(
        self, user_id: str, skill_name: str, new_confidence: float, source: str = "self_declared"
    ) -> CareerTwin:
        twin = await self.get_twin(user_id)
        new_confidence = max(0.0, min(1.0, new_confidence))
        year = datetime.now(timezone.utc).year
        skills = copy.deepcopy(twin.skills or [])
        found = False
        for s in skills:
            if s.get("name", "").lower() == skill_name.lower():
                s["confidence"] = new_confidence
                s["recency_score"] = 1.0
                s["last_used_year"] = year
                s["source"] = source
                found = True
                break
        if not found:
            skills.append(self._new_skill(skill_name, "", new_confidence, twin.total_years_experience, year, source))
        twin.skills = skills
        self._touch(twin, "skills")
        self._recompute_scores(twin)
        await self.db.flush()
        return twin

    async def mark_skill_learned(self, user_id: str, skill_name: str) -> CareerTwin:
        twin = await self.get_twin(user_id)
        year = datetime.now(timezone.utc).year
        skills = copy.deepcopy(twin.skills or [])
        found = False
        for s in skills:
            if s.get("name", "").lower() == skill_name.lower():
                s["confidence"] = max(s.get("confidence", 0.0), 0.7)
                s["depth"] = "working"
                s["recency_score"] = 1.0
                s["last_used_year"] = year
                s["source"] = "learned"
                found = True
                break
        if not found:
            skills.append(self._new_skill(skill_name, "", 0.7, 0.0, year, "learned"))
        twin.skills = skills
        # learning_velocity: skills added per month since twin creation
        twin.learning_velocity = self._learning_velocity(twin, learned_delta=0 if found else 1)
        self._touch(twin, "skills")
        self._recompute_scores(twin)
        await self.db.flush()
        return twin

    async def add_interview_result(self, user_id: str, interview_data: dict) -> CareerTwin:
        twin = await self.get_twin(user_id)
        history = list(twin.interview_history or [])
        entry = {
            "company": interview_data.get("company", ""),
            "role": interview_data.get("role", ""),
            "date": interview_data.get("date") or _now(),
            "outcome": interview_data.get("outcome", ""),
            "weak_topics": interview_data.get("weak_topics", []),
            "strong_topics": interview_data.get("strong_topics", []),
            "notes": interview_data.get("notes", ""),
        }
        history.append(entry)
        twin.interview_history = history

        weaknesses = list(twin.known_weaknesses or [])
        for t in entry["weak_topics"]:
            if t not in weaknesses:
                weaknesses.append(t)
        twin.known_weaknesses = weaknesses

        strengths = list(twin.strengths or [])
        for t in entry["strong_topics"]:
            if t not in strengths:
                strengths.append(t)
        twin.strengths = strengths

        # Interview weak topics reduce confidence of matching skills.
        skills = copy.deepcopy(twin.skills or [])
        weak_lower = {t.lower() for t in entry["weak_topics"]}
        for s in skills:
            if s.get("name", "").lower() in weak_lower:
                s["confidence"] = max(0.0, s.get("confidence", 0.5) - 0.15)
                s["source"] = "interview_result"
        twin.skills = skills

        self._touch(twin, "interview")
        self._touch(twin, "skills")
        self._recompute_scores(twin)
        await self.db.flush()
        return twin

    async def compute_all_scores(self, user_id: str) -> CareerTwin:
        twin = await self.get_twin(user_id)
        self._recompute_scores(twin)
        await self.db.flush()
        return twin

    async def get_weekly_delta(self, user_id: str) -> dict:
        twin = await self.get_twin(user_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        changed = []
        for field, ts in (twin.change_log or {}).items():
            try:
                when = datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when >= cutoff:
                changed.append({"field": field, "changed_at": ts})
        return {
            "week_start": cutoff.isoformat(),
            "changed_fields": changed,
            "changed_count": len(changed),
            "current_scores": {
                "embedded_domain_score": twin.embedded_domain_score,
                "profile_completeness": twin.profile_completeness,
                "interview_readiness_score": twin.interview_readiness_score,
                "market_value_score": twin.market_value_score,
            },
        }

    # ── Phase 3 aliases / long-term memory helpers ────────────────────────
    async def init_from_resume(self, user_id: str, resume_id: str) -> CareerTwin:
        """Public alias for :meth:`create_from_resume`."""
        return await self.create_from_resume(user_id, resume_id)

    async def get_or_create(self, user_id: str) -> CareerTwin:
        """Return the user's twin, creating a minimal empty one if absent."""
        twin = await self.repo.get_by_user(user_id)
        if twin:
            return twin
        now = _now()
        twin = await self.repo.create(user_id=user_id, last_synced_at=now, change_log={"identity": now})
        await self.db.flush()
        return twin

    async def recompute_scores(self, user_id: str) -> CareerTwin:
        """Public alias for :meth:`compute_all_scores`."""
        return await self.compute_all_scores(user_id)

    async def get_summary(self, user_id: str) -> dict:
        """Public alias for :meth:`get_twin_summary`."""
        return await self.get_twin_summary(user_id)

    async def update_after_interview(self, user_id: str, interview_result: dict) -> CareerTwin:
        """Record an interview and refresh interview aggregates on the twin."""
        twin = await self.add_interview_result(user_id, interview_result)

        history = [dict(h) for h in (twin.interview_history or [])]
        if history and interview_result.get("score") is not None:
            history[-1]["score"] = interview_result["score"]
        twin.interview_history = history
        twin.interviews_completed = len(history)

        scores = [
            float(h["score"]) for h in history
            if isinstance(h, dict) and h.get("score") is not None
        ]
        twin.avg_interview_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        weak = list(twin.weak_interview_topics or [])
        for t in interview_result.get("weak_topics", []) or []:
            if t not in weak:
                weak.append(t)
        twin.weak_interview_topics = weak

        self._touch(twin, "interview")
        await self.db.flush()
        return twin

    async def update_after_learning(self, user_id: str, skill: str, session_result: dict) -> CareerTwin:
        """Record a completed learning session: skill, streak, monthly log."""
        twin = await self.mark_skill_learned(user_id, skill)

        today = datetime.now(timezone.utc).date()
        last = twin.last_active_date
        last_date = None
        if last:
            try:
                last_date = datetime.fromisoformat(last).date()
            except ValueError:
                last_date = None
        if last_date == today:
            pass  # already active today; streak unchanged
        elif last_date == today - timedelta(days=1):
            twin.learning_streak_days = (twin.learning_streak_days or 0) + 1
        else:
            twin.learning_streak_days = 1
        twin.last_active_date = today.isoformat()

        month_key = today.strftime("%Y-%m")
        learned = [e for e in (twin.skills_learned_this_month or []) if e.get("date", "").startswith(month_key)]
        learned.append({"skill": skill, "date": today.isoformat(), "score": session_result.get("score")})
        twin.skills_learned_this_month = learned

        self._touch(twin, "learning")
        await self.db.flush()
        return twin

    # ── Serialization ─────────────────────────────────────────────────────
    def to_dict(self, twin: CareerTwin) -> dict:
        return {
            "id": twin.id,
            "user_id": twin.user_id,
            "full_name": twin.full_name,
            "email": twin.email,
            "phone": twin.phone,
            "location": twin.location,
            "linkedin_url": twin.linkedin_url,
            "github_url": twin.github_url,
            "skills": twin.skills or [],
            "experience_entries": twin.experience_entries or [],
            "total_years_experience": twin.total_years_experience,
            "current_role": twin.current_role,
            "current_company": twin.current_company,
            "current_salary_lpa": twin.current_salary_lpa,
            "target_salary_lpa": twin.target_salary_lpa,
            "career_level": twin.career_level,
            "career_trajectory": twin.career_trajectory,
            "embedded_domain_score": twin.embedded_domain_score,
            "profile_completeness": twin.profile_completeness,
            "interview_readiness_score": twin.interview_readiness_score,
            "market_value_score": twin.market_value_score,
            "learning_velocity": twin.learning_velocity,
            "dream_companies": twin.dream_companies or [],
            "preferred_locations": twin.preferred_locations or [],
            "preferred_domains": twin.preferred_domains or [],
            "work_mode_preference": twin.work_mode_preference,
            "min_salary_lpa": twin.min_salary_lpa,
            "open_to_relocation": twin.open_to_relocation,
            "education_entries": twin.education_entries or [],
            "certifications": twin.certifications or [],
            "projects": twin.projects or [],
            "interview_history": twin.interview_history or [],
            "strengths": twin.strengths or [],
            "known_weaknesses": twin.known_weaknesses or [],
            "interview_style_notes": twin.interview_style_notes,
            "version": twin.version,
            "source_resume_id": twin.source_resume_id,
            "updated_at": str(twin.updated_at),
        }

    # ── Internal helpers ──────────────────────────────────────────────────
    def _skills_from_profile(self, profile: CandidateProfile, year: int) -> list[dict]:
        skills: list[dict] = []
        seen: set[str] = set()
        for attr, category in _CATEGORY_FIELDS:
            for name in getattr(profile, attr, []) or []:
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                skills.append(
                    self._new_skill(name, category, 0.6, profile.total_years_experience, year, "resume")
                )
        return skills

    def _new_skill(self, name, category, confidence, years, year, source) -> dict:
        return {
            "name": name,
            "category": category,
            "confidence": confidence,
            "depth": "working" if confidence >= 0.6 else "exposure",
            "years_used": years,
            "recency_score": 1.0,
            "last_used_year": year,
            "source": source,
        }

    def _education_from_profile(self, profile: CandidateProfile) -> list[dict]:
        if not profile.highest_degree:
            return []
        return [{
            "institution": "",
            "degree": profile.highest_degree,
            "field": profile.field_of_study,
            "year": profile.graduation_year,
            "cgpa": None,
        }]

    def _career_level(self, years: float) -> str:
        if years < 2:
            return "junior"
        if years < 5:
            return "mid"
        if years < 9:
            return "senior"
        if years < 13:
            return "lead"
        return "principal"

    def _learning_velocity(self, twin: CareerTwin, learned_delta: int) -> float:
        try:
            created = twin.created_at
            if created is None:
                return twin.learning_velocity or 0.0
            months = max(1.0, (datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)).days / 30.0)
        except Exception:  # noqa: BLE001
            months = 1.0
        learned = sum(1 for s in (twin.skills or []) if s.get("source") == "learned")
        return round((learned + learned_delta) / months, 2)

    def _touch(self, twin: CareerTwin, field: str) -> None:
        log = dict(twin.change_log or {})
        log[field] = _now()
        twin.change_log = log

    def _recompute_scores(self, twin: CareerTwin, profile: CandidateProfile | None = None) -> None:
        skills = twin.skills or []
        names = {s.get("name", "").lower() for s in skills}
        core = {"c", "c++", "rtos", "freertos", "embedded", "firmware", "arm", "cortex-m",
                "autosar", "can", "lin", "spi", "i2c", "device driver", "bare metal",
                "iso 26262", "linux kernel", "bsp"}
        matched_core = names & core
        domain = min(100, int(len(matched_core) / len(core) * 100))
        if any(s.get("category") == "automotive" for s in skills):
            domain = min(100, domain + 10)
        if twin.total_years_experience > 2:
            domain = min(100, domain + 5)
        twin.embedded_domain_score = domain

        completeness = 0
        if twin.full_name:
            completeness += 15
        if twin.email:
            completeness += 10
        if twin.total_years_experience > 0:
            completeness += 20
        if len(skills) >= 5:
            completeness += 25
        if twin.education_entries:
            completeness += 15
        if domain >= 40:
            completeness += 15
        twin.profile_completeness = min(100, completeness)

        avg_conf = (sum(s.get("confidence", 0.0) for s in skills) / len(skills)) if skills else 0.0
        readiness = int(avg_conf * 70 + min(30, len(skills) * 2))
        twin.interview_readiness_score = max(0, min(100, readiness))

        market = int(min(60, twin.total_years_experience * 6) + min(40, len(skills) * 2))
        twin.market_value_score = max(0, min(100, market))

        self._touch(twin, "scores")
