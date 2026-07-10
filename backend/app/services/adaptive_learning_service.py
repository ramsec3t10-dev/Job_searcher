"""EMBEDHUNT AI — Adaptive Learning Service.

Turns the Career Twin plus the live job market into a single, high-signal daily
action: the one skill worth an hour today. Also owns spaced-repetition review
scheduling and post-session twin updates.

Skill selection blends four signals:
    (job_demand × 0.4) + ((1 - confidence) × 0.3)
    + (salary_impact × 0.2) + (recency_penalty × 0.1)

The daily mission is computed once per day and cached for 24h (persisted as a
memory entry) so repeated opens never recompute or re-bill the LLM.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.learning_agent import LearningAgent
from app.agents.models import DailyMission
from app.config.logging import get_logger
from app.models.career_twin import CareerTwin
from app.models.memory import MemoryEntry
from app.recommendation.engine import run_matching
from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.memory_repository import MemoryRepository
from app.resume.normalizer import CandidateProfile
from app.services.career_twin_service import CareerTwinService

logger = get_logger(__name__)

# Confidence below this marks a skill as "needs work".
_LOW_CONFIDENCE = 0.7
# Spaced-repetition ladder (days between reviews).
SPACED_INTERVALS = [1, 3, 7, 14, 30]
# Memory types used as durable, per-user key/value stores.
_MISSION_MEMORY = "daily_mission"
_REVIEW_MEMORY = "spaced_repetition"
# Salary normaliser: LPA that maps to a full 1.0 salary_impact.
_SALARY_CAP_LPA = 50.0

# Twin skill category -> CandidateProfile bucket.
_CATEGORY_TO_PROFILE = {
    "programming": "programming_languages",
    "rtos": "rtos_and_os",
    "protocols": "protocols",
    "hardware": "hardware_platforms",
    "automotive": "automotive_safety",
    "tools": "tools_and_debug",
    "concepts": "software_concepts",
}


def _today() -> date:
    return datetime.now(timezone.utc).date()


class AdaptiveLearningService:
    def __init__(self, db: AsyncSession, router=None):
        self.db = db
        self.twin_repo = CareerTwinRepository(db)
        self.twin_service = CareerTwinService(db)
        self.memory_repo = MemoryRepository(db, router=router)

    # ── Daily mission ─────────────────────────────────────────────────────
    async def get_daily_mission(self, user_id: str) -> DailyMission:
        cached = await self._cached_mission(user_id)
        if cached is not None:
            return cached

        twin = await self.twin_repo.get_by_user(user_id)
        skills = list((twin.skills if twin else None) or [])
        low = [s for s in skills if float(s.get("confidence", 1.0)) < _LOW_CONFIDENCE]

        focus = self._select_focus_skill(twin, low)
        skill_name = focus.get("name", "") if focus else ""
        topic = self._top_topic(focus) if focus else ""

        lesson = await LearningAgent(self.db).create_lesson(user_id, skill_name, topic)
        mission = DailyMission(
            skill=skill_name,
            topic=topic or skill_name,
            duration_minutes=self._duration_for(focus),
            lesson=lesson,
            quiz=list(lesson.quiz),
            why_today=self._why_today(focus),
        )
        await self._store_mission(user_id, mission)
        return mission

    def _select_focus_skill(self, twin: Optional[CareerTwin], low: list[dict]) -> Optional[dict]:
        if not low:
            return None
        top_jobs = self._top_matched_jobs(twin)
        demand = Counter()
        salary_by_skill: dict[str, float] = {}
        for job in top_jobs:
            for name in (job.match.matched_skills or []):
                key = name.lower()
                demand[key] += 1
                sal = job.salary_max_lpa or job.salary_min_lpa or 0.0
                salary_by_skill[key] = max(salary_by_skill.get(key, 0.0), float(sal))
        n = max(1, len(top_jobs))

        def score(skill: dict) -> float:
            key = skill.get("name", "").lower()
            confidence = float(skill.get("confidence", 0.0))
            job_demand = demand.get(key, 0) / n
            salary_impact = min(1.0, salary_by_skill.get(key, 0.0) / _SALARY_CAP_LPA)
            recency_penalty = 1.0 - float(skill.get("recency_score", 1.0))
            return (
                job_demand * 0.4
                + (1.0 - confidence) * 0.3
                + salary_impact * 0.2
                + recency_penalty * 0.1
            )

        return max(low, key=score)

    def _top_matched_jobs(self, twin: Optional[CareerTwin]):
        if twin is None:
            return []
        profile = self._twin_to_profile(twin)
        try:
            result = run_matching(profile, min_score=0)
        except Exception as exc:  # noqa: BLE001 — matching must never break the mission
            logger.warning("adaptive_matching_failed", error=str(exc))
            return []
        return result.jobs[:20]

    @staticmethod
    def _twin_to_profile(twin: CareerTwin) -> CandidateProfile:
        buckets: dict[str, list[str]] = {v: [] for v in _CATEGORY_TO_PROFILE.values()}
        all_skills: list[str] = []
        for s in twin.skills or []:
            name = s.get("name", "")
            if not name:
                continue
            all_skills.append(name)
            field = _CATEGORY_TO_PROFILE.get(s.get("category", ""))
            if field:
                buckets[field].append(name)
        return CandidateProfile(
            name_hint=twin.full_name or "",
            total_years_experience=twin.total_years_experience or 0.0,
            current_role=twin.current_role or None,
            current_company=twin.current_company or None,
            all_skills=all_skills,
            skill_count=len(all_skills),
            embedded_domain_score=twin.embedded_domain_score or 0,
            **buckets,
        )

    @staticmethod
    def _top_topic(skill: dict) -> str:
        # Without a topic taxonomy the skill itself is the topic to teach today.
        return skill.get("name", "")

    @staticmethod
    def _duration_for(skill: Optional[dict]) -> int:
        if not skill:
            return 20
        confidence = float(skill.get("confidence", 0.0))
        # Weaker skills earn a longer session.
        return 45 if confidence < 0.4 else 30

    @staticmethod
    def _why_today(skill: Optional[dict]) -> str:
        if not skill:
            return "Your profile is strong today — keep momentum with a quick refresher."
        name = skill.get("name", "this skill")
        confidence = int(float(skill.get("confidence", 0.0)) * 100)
        return (
            f"{name} is in high demand across your top job matches and your current "
            f"confidence is {confidence}%. Closing this gap raises your match rate the most."
        )

    # ── Spaced repetition ─────────────────────────────────────────────────
    async def update_spaced_repetition(self, user_id: str, skill: str, was_confident: bool) -> dict:
        entry = await self._review_entry(user_id, skill)
        state = self._load_state(entry)

        if was_confident:
            state["interval_index"] = min(state["interval_index"] + 1, len(SPACED_INTERVALS) - 1)
            state["consecutive_confident"] = state["consecutive_confident"] + 1
        else:
            state["interval_index"] = 0
            state["consecutive_confident"] = 0

        interval_days = SPACED_INTERVALS[state["interval_index"]]
        next_review = _today() + timedelta(days=interval_days)
        state["skill"] = skill
        state["next_review_date"] = next_review.isoformat()

        payload = json.dumps(state)
        if entry is not None:
            entry.summary = f"Review {skill} on {state['next_review_date']}"
            entry.full_content = payload
            await self.db.flush()
        else:
            await self.memory_repo.store(
                user_id,
                _REVIEW_MEMORY,
                f"Review {skill} on {state['next_review_date']}",
                full_content=payload,
                importance_score=3,
                tags=[skill],
            )
        return state

    async def get_review_queue(self, user_id: str) -> list[str]:
        today = _today()
        rows = await self._review_entries(user_id)
        due: list[tuple[int, str]] = []
        for entry in rows:
            state = self._load_state(entry)
            try:
                next_review = date.fromisoformat(state["next_review_date"])
            except (ValueError, KeyError, TypeError):
                continue
            if next_review <= today:
                overdue = (today - next_review).days
                due.append((overdue, state.get("skill", "")))
        due.sort(key=lambda t: t[0], reverse=True)
        return [skill for _, skill in due if skill]

    # ── Session completion ────────────────────────────────────────────────
    async def track_session_complete(
        self, user_id: str, skill: str, duration_minutes: int, quiz_score: float
    ) -> None:
        delta = 0.05 if quiz_score > 0.7 else -0.02
        current = self._current_confidence(await self.twin_repo.get_by_user(user_id), skill)
        await self.twin_service.update_skill_confidence(
            user_id, skill, current + delta, source="learning_session"
        )
        await self._bump_streak(user_id)
        await self.memory_repo.store(
            user_id,
            "learning",
            f"Completed {duration_minutes}min {skill} session. Quiz: {quiz_score * 100:.0f}%",
            importance_score=3,
            tags=[skill, "learning_session"],
        )
        try:
            await self.twin_service.recompute_scores(user_id)
        except Exception as exc:  # noqa: BLE001 — recompute is best-effort
            logger.warning("adaptive_recompute_failed", error=str(exc))

    @staticmethod
    def _current_confidence(twin: Optional[CareerTwin], skill: str) -> float:
        for s in (twin.skills if twin else None) or []:
            if s.get("name", "").lower() == skill.lower():
                return float(s.get("confidence", 0.0))
        return 0.0

    async def _bump_streak(self, user_id: str) -> None:
        twin = await self.twin_service.get_twin(user_id)
        today = _today()
        last = twin.last_active_date
        last_date = None
        if last:
            try:
                last_date = date.fromisoformat(last[:10])
            except ValueError:
                last_date = None
        if last_date == today:
            pass
        elif last_date == today - timedelta(days=1):
            twin.learning_streak_days = (twin.learning_streak_days or 0) + 1
        else:
            twin.learning_streak_days = 1
        twin.last_active_date = today.isoformat()
        await self.db.flush()

    # ── Persistence helpers ───────────────────────────────────────────────
    async def _cached_mission(self, user_id: str) -> Optional[DailyMission]:
        rows = await self.memory_repo.get_recent(
            user_id, memory_type=_MISSION_MEMORY, limit=1
        )
        if not rows:
            return None
        entry = rows[0]
        created = entry.created_at
        if not created or created.astimezone(timezone.utc).date() != _today():
            return None
        if not entry.full_content:
            return None
        try:
            return DailyMission(**json.loads(entry.full_content))
        except (ValueError, TypeError):
            return None

    async def _store_mission(self, user_id: str, mission: DailyMission) -> None:
        await self.memory_repo.store(
            user_id,
            _MISSION_MEMORY,
            f"Daily mission: {mission.skill}",
            full_content=mission.model_dump_json(),
            importance_score=2,
            tags=[_MISSION_MEMORY, _today().isoformat()],
        )

    async def _review_entries(self, user_id: str) -> list[MemoryEntry]:
        stmt = select(MemoryEntry).where(
            MemoryEntry.user_id == user_id,
            MemoryEntry.memory_type == _REVIEW_MEMORY,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _review_entry(self, user_id: str, skill: str) -> Optional[MemoryEntry]:
        for entry in await self._review_entries(user_id):
            state = self._load_state(entry)
            if state.get("skill", "").lower() == skill.lower():
                return entry
        return None

    @staticmethod
    def _load_state(entry: Optional[MemoryEntry]) -> dict:
        state = {"interval_index": 0, "consecutive_confident": 0}
        if entry is not None and entry.full_content:
            try:
                state.update(json.loads(entry.full_content))
            except (ValueError, TypeError):
                pass
        state.setdefault("interval_index", 0)
        state.setdefault("consecutive_confident", 0)
        return state
