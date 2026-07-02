"""EMBEDHUNT AI — Feedback loop service.

Records user/outcome feedback on jobs and turns it into learning signals:
  * per-skill and per-company affinities (aggregated, clamped to [-1, 1])
  * a re-ranking boost the matching layer can apply to future recommendations
  * CareerTwin updates — strong positive/negative outcomes reinforce strengths /
    known weaknesses.

Deterministic and side-effect isolated: twin updates only occur when a twin
exists, so feedback never fails for users who haven't initialized one.
"""
from __future__ import annotations

import copy

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import FeedbackEvent, FeedbackType
from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.feedback_repository import FeedbackEventRepository

# Signal weights per feedback type (positive ⇒ reinforce, negative ⇒ discourage).
_SIGNALS: dict[str, float] = {
    FeedbackType.SAVED.value: 0.3,
    FeedbackType.APPLIED.value: 0.4,
    FeedbackType.SHORTLISTED.value: 0.7,
    FeedbackType.INTERVIEW.value: 0.8,
    FeedbackType.OFFER.value: 1.0,
    FeedbackType.REC_POSITIVE.value: 0.5,
    FeedbackType.DISMISSED.value: -0.4,
    FeedbackType.REJECTED.value: -0.6,
    FeedbackType.GHOSTED.value: -0.2,
    FeedbackType.REC_NEGATIVE.value: -0.5,
}

_STRONG_POSITIVE = {FeedbackType.SHORTLISTED.value, FeedbackType.INTERVIEW.value, FeedbackType.OFFER.value}


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _split_skills(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [s.strip().lower() for s in raw if s and s.strip()]
    return [s.strip().lower() for s in raw.replace(";", ",").split(",") if s.strip()]


class FeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FeedbackEventRepository(db)
        self.twin_repo = CareerTwinRepository(db)

    async def record_feedback(self, user_id: str, feedback_type: str, *,
                              job_id: str = "", company: str = "",
                              company_tier: str = "", skills=None,
                              match_score: int = 0, note: str | None = None) -> dict:
        if feedback_type not in _SIGNALS:
            raise ValueError(f"Unknown feedback_type: {feedback_type}")
        skill_list = _split_skills(skills)
        signal = _SIGNALS[feedback_type]
        event = FeedbackEvent(
            user_id=user_id, job_id=job_id, feedback_type=feedback_type,
            signal=signal, company=company, company_tier=company_tier,
            skills=",".join(skill_list), match_score=match_score, note=note,
        )
        self.db.add(event)
        await self.db.flush()
        await self._apply_to_twin(user_id, feedback_type, skill_list)
        return {
            "id": event.id,
            "feedback_type": feedback_type,
            "signal": signal,
            "job_id": job_id,
        }

    async def get_affinities(self, user_id: str) -> dict:
        events = await self.repo.list_for_user(user_id)
        skill_sum: dict[str, float] = {}
        skill_cnt: dict[str, int] = {}
        company_sum: dict[str, float] = {}
        company_cnt: dict[str, int] = {}
        for e in events:
            for s in _split_skills(e.skills):
                skill_sum[s] = skill_sum.get(s, 0.0) + e.signal
                skill_cnt[s] = skill_cnt.get(s, 0) + 1
            if e.company:
                c = e.company.lower()
                company_sum[c] = company_sum.get(c, 0.0) + e.signal
                company_cnt[c] = company_cnt.get(c, 0) + 1
        skill_aff = {k: round(_clamp(skill_sum[k] / skill_cnt[k]), 3) for k in skill_sum}
        company_aff = {k: round(_clamp(company_sum[k] / company_cnt[k]), 3) for k in company_sum}
        return {"skill_affinity": skill_aff, "company_affinity": company_aff, "event_count": len(events)}

    async def get_feedback_summary(self, user_id: str) -> dict:
        events = await self.repo.list_for_user(user_id)
        by_type: dict[str, int] = {}
        for e in events:
            by_type[e.feedback_type] = by_type.get(e.feedback_type, 0) + 1
        aff = await self.get_affinities(user_id)
        top_skills = sorted(aff["skill_affinity"].items(), key=lambda kv: kv[1], reverse=True)[:5]
        avoid_skills = sorted(aff["skill_affinity"].items(), key=lambda kv: kv[1])[:5]
        return {
            "total_events": len(events),
            "by_type": by_type,
            "preferred_skills": [k for k, v in top_skills if v > 0],
            "aversive_skills": [k for k, v in avoid_skills if v < 0],
            "company_affinity": aff["company_affinity"],
        }

    def apply_affinity(self, matches: list, skill_affinity: dict,
                       company_affinity: dict, weight: float = 8.0) -> list:
        """Re-rank matches (UnifiedMatch-like) with learned affinities. Pure/in-place safe."""
        adjusted = []
        for m in matches:
            boost = 0.0
            for s in getattr(m, "matched_skills", []) or []:
                boost += skill_affinity.get(s.lower(), 0.0)
            comp = getattr(m, "company", "").lower()
            boost += company_affinity.get(comp, 0.0)
            new_score = int(max(0, min(99, round(getattr(m, "total_score", 0) + boost * weight))))
            m.total_score = new_score
            adjusted.append(m)
        adjusted.sort(key=lambda m: -getattr(m, "total_score", 0))
        for i, m in enumerate(adjusted, 1):
            if hasattr(m, "rank"):
                m.rank = i
        return adjusted

    async def _apply_to_twin(self, user_id: str, feedback_type: str, skills: list[str]) -> None:
        twin = await self.twin_repo.get_by_user(user_id)
        if twin is None or not skills:
            return
        if feedback_type in _STRONG_POSITIVE:
            strengths = list(twin.strengths or [])
            for s in skills:
                if s not in strengths:
                    strengths.append(s)
            twin.strengths = strengths
        elif feedback_type == FeedbackType.REJECTED.value:
            # rejection reduces confidence of the job's skills the candidate claims
            updated = copy.deepcopy(twin.skills or [])
            job_skills = {s.lower() for s in skills}
            for entry in updated:
                if entry.get("name", "").lower() in job_skills:
                    entry["confidence"] = max(0.0, entry.get("confidence", 0.5) - 0.05)
            twin.skills = updated
        await self.db.flush()
