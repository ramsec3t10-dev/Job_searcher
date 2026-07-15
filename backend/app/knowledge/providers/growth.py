"""Growth providers: Learning, Interview, Goals, Habits, Professional Growth."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.base import KnowledgeLayerProvider, LayerData
from app.knowledge.layers import KnowledgeLayer
from app.knowledge.providers._shared import current_streak, load_twin
from app.models.application import Application, ApplicationOutcome
from app.models.interview import InterviewSession
from app.models.roadmap import LearningRoadmap
from app.repositories.daily_checkin_repository import DailyCheckinRepository


class LearningProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.LEARNING
    source = "learning_roadmaps"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        roadmap = (
            await session.execute(
                select(LearningRoadmap)
                .where(LearningRoadmap.user_id == user_id, LearningRoadmap.is_active == True)  # noqa: E712
                .order_by(LearningRoadmap.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if roadmap is None:
            return None
        facts = {
            "target_job_title": roadmap.target_job_title,
            "progress_pct": roadmap.progress_pct,
            "total_gap_skills": roadmap.total_gap_skills,
            "estimated_weeks": roadmap.estimated_weeks,
            "score_before": roadmap.score_before,
            "score_after_estimated": roadmap.score_after_estimated,
        }
        summary = (
            f"Roadmap → {roadmap.target_job_title}: {roadmap.progress_pct}% done, "
            f"{roadmap.total_gap_skills} gap skills, ~{roadmap.estimated_weeks} weeks"
        )
        return self._data(summary, facts)


class InterviewProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.INTERVIEW
    source = "interview_sessions+career_twins"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        sessions = (
            await session.execute(
                select(InterviewSession).where(InterviewSession.user_id == user_id)
            )
        ).scalars().all()
        twin = await load_twin(ctx, session, user_id)
        if not sessions and twin is None:
            return None
        readiness = 0
        if sessions:
            readiness = max(s.readiness_score for s in sessions)
        elif twin is not None:
            readiness = twin.interview_readiness_score
        completed = twin.interviews_completed if twin else 0
        avg_score = twin.avg_interview_score if twin else 0.0
        weak = list(twin.weak_interview_topics or []) if twin else []
        facts = {
            "prep_sessions": len(sessions),
            "readiness_score": readiness,
            "interviews_completed": completed,
            "avg_interview_score": avg_score,
            "weak_topics": weak,
        }
        weak_str = f"; weak: {', '.join(weak[:3])}" if weak else ""
        summary = (
            f"Interview readiness {readiness}/100, {len(sessions)} prep sessions, "
            f"{completed} completed (avg {avg_score:.0f}){weak_str}"
        )
        return self._data(summary, facts)


class GoalsProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.GOALS
    source = "career_twins.career_goals"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        goals = (twin.career_goals or {}) if twin else {}
        if not goals:
            return None
        short_term = goals.get("short_term", "")
        long_term = goals.get("long_term", "")
        target_role = goals.get("target_role", "")
        facts = {"short_term": short_term, "long_term": long_term, "target_role": target_role}
        parts = [p for p in (
            f"target: {target_role}" if target_role else "",
            f"short-term: {short_term}" if short_term else "",
            f"long-term: {long_term}" if long_term else "",
        ) if p]
        return self._data("; ".join(parts), facts)


class HabitsProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.HABITS
    source = "daily_checkins+career_twins"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        dates = await DailyCheckinRepository(session).list_dates(user_id)
        twin = await load_twin(ctx, session, user_id)
        learning_streak = twin.learning_streak_days if twin else 0
        if not dates and not learning_streak:
            return None
        streak = current_streak(dates)
        from datetime import date, timedelta

        last_7 = {(date.today() - timedelta(days=i)).isoformat() for i in range(7)}
        checkins_7d = len(set(dates) & last_7)
        facts = {
            "current_streak_days": streak,
            "checkins_last_7d": checkins_7d,
            "learning_streak_days": learning_streak,
        }
        summary = f"{streak}-day check-in streak, {checkins_7d}/7 this week; learning streak {learning_streak}d"
        return self._data(summary, facts)


class ProfessionalGrowthProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.PROFESSIONAL_GROWTH
    source = "career_twins+applications"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        outcomes = (
            await session.execute(
                select(Application.outcome, func.count())
                .where(Application.user_id == user_id)
                .group_by(Application.outcome)
            )
        ).all()
        by_outcome = {getattr(o, "value", str(o)): int(n) for o, n in outcomes}
        interviews = by_outcome.get(ApplicationOutcome.INTERVIEW.value, 0)
        offers = by_outcome.get(ApplicationOutcome.OFFER.value, 0)
        if twin is None and not by_outcome:
            return None
        learned = list(twin.skills_learned_this_month or []) if twin else []
        facts = {
            "twin_version": twin.version if twin else 0,
            "learning_velocity": twin.learning_velocity if twin else 0.0,
            "skills_learned_this_month": len(learned),
            "market_value_score": twin.market_value_score if twin else 0,
            "interviews": interviews,
            "offers": offers,
        }
        summary = (
            f"{len(learned)} skills learned this month, {interviews} interviews / {offers} offers; "
            f"market value {facts['market_value_score']}/100"
        )
        return self._data(summary, facts)
