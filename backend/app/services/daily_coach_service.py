"""EMBEDHUNT AI — Daily coach service.

Composes a personalised daily brief from the CareerTwin (source of truth),
discovered-job pipeline, and check-in streak. Fully graceful: with no twin it
returns an onboarding brief instead of failing.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.daily_checkin_repository import DailyCheckinRepository
from app.repositories.discovered_job_repository import DiscoveredJobRepository

_CONFIDENT = 0.6


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _greeting() -> str:
    hour = datetime.now(timezone.utc).hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


def _motivation(readiness: int, streak: int) -> str:
    if streak >= 7:
        return f"{streak}-day streak — consistency like this is exactly how offers happen."
    if readiness >= 80:
        return "You're interview-ready. Keep applying and stay sharp."
    if readiness >= 55:
        return "You're close. A little focused prep each day compounds fast."
    return "Small daily progress beats occasional bursts. Do one focused thing today."


class DailyCoachService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_repo = CareerTwinRepository(db)
        self.checkin_repo = DailyCheckinRepository(db)
        self.jobs_repo = DiscoveredJobRepository(db)

    async def get_daily_brief(self, user_id: str) -> dict:
        streak = await self._streak(user_id)
        twin = await self.twin_repo.get_by_user(user_id)
        if twin is None:
            return {
                "date": _today(),
                "greeting": _greeting(),
                "streak_days": streak,
                "onboarding": True,
                "focus_today": ["Upload your resume to initialize your Career Twin."],
                "motivation": "Your journey starts with one upload. Let's build your Career Twin.",
            }

        skills = twin.skills or []
        weak = sorted(
            [s for s in skills if 0 < float(s.get("confidence", 0.0)) < _CONFIDENT],
            key=lambda s: float(s.get("confidence", 0.0)),
        )
        focus_skills = [s.get("name", "") for s in weak[:3]]
        if not focus_skills:
            focus_skills = list(twin.known_weaknesses or [])[:3]
        focus_today = [f"Study & practice: {s}" for s in focus_skills] or \
            ["Apply to 3 strong-match roles today."]

        new_matches = await self.jobs_repo.count_active()
        readiness = int(twin.interview_readiness_score or 0)

        return {
            "date": _today(),
            "greeting": _greeting(),
            "streak_days": streak,
            "onboarding": False,
            "career_snapshot": {
                "career_level": twin.career_level,
                "profile_completeness": twin.profile_completeness,
                "interview_readiness_score": readiness,
                "market_value_score": twin.market_value_score,
                "embedded_domain_score": twin.embedded_domain_score,
            },
            "whats_new": {"active_job_matches": new_matches},
            "focus_today": focus_today,
            "interview_nudge": self._interview_nudge(readiness),
            "weekly_delta": await self._weekly_delta(twin),
            "motivation": _motivation(readiness, streak),
        }

    async def check_in(self, user_id: str, tasks_completed: int = 0, note: str | None = None) -> dict:
        today = _today()
        existing = await self.checkin_repo.get_for_date(user_id, today)
        if existing is None:
            existing = await self.checkin_repo.create(
                user_id=user_id, checkin_date=today,
                tasks_completed=max(0, tasks_completed), note=note)
        else:
            existing.tasks_completed = max(existing.tasks_completed, tasks_completed)
            if note:
                existing.note = note
            await self.db.flush()
        streak = await self._streak(user_id)
        return {"date": today, "streak_days": streak,
                "tasks_completed": existing.tasks_completed}

    async def _streak(self, user_id: str) -> int:
        dates = set(await self.checkin_repo.list_dates(user_id))
        if not dates:
            return 0
        today = datetime.now(timezone.utc).date()
        # streak counts back from today, or yesterday if not yet checked in today
        start = today if today.isoformat() in dates else today - timedelta(days=1)
        streak = 0
        cursor = start
        while cursor.isoformat() in dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    @staticmethod
    def _interview_nudge(readiness: int) -> str:
        if readiness >= 75:
            return "Run a timed mock interview to stay sharp."
        if readiness >= 45:
            return "Do a 5-question mock on your weakest topic today."
        return "Start with fundamentals — one mock interview builds momentum."

    @staticmethod
    async def _weekly_delta(twin) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        changed = 0
        for _field, ts in (twin.change_log or {}).items():
            try:
                when = datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when >= cutoff:
                changed += 1
        return {"changed_fields_this_week": changed}
