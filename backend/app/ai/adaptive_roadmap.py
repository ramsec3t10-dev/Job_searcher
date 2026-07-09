"""EMBEDHUNT AI — Adaptive learning roadmap (Module 9).

Unlike the static planner, this engine adapts to the CareerTwin: it distinguishes
brand-new skill *gaps* from low-confidence *reinforcements* (quick wins),
prioritises by market demand + learned feedback affinity + effort, schedules the
plan into weekly capacity, and projects the match-score trajectory with
milestones. Progress-aware: skills the twin already holds confidently are dropped.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.config.logging import get_logger
from app.config.settings import settings
from app.roadmap.planner import (
    DEFAULT_HOURS,
    DEFAULT_RESOURCES,
    SKILL_HOURS,
    SKILL_RESOURCES,
    SkillLevel,
)

logger = get_logger(__name__)

_CONFIDENT = 0.6  # confidence at/above which a skill counts as "have"


@dataclass
class AdaptiveTask:
    skill: str
    kind: str  # "gap" | "reinforcement"
    priority: int
    estimated_hours: int
    level: str
    demand: int
    affinity: float
    score_delta: int
    week: int
    resources: list[dict]

    def to_dict(self) -> dict:
        return {
            "skill": self.skill, "kind": self.kind, "priority": self.priority,
            "estimated_hours": self.estimated_hours, "level": self.level,
            "demand": self.demand, "affinity": self.affinity,
            "score_delta": self.score_delta, "week": self.week,
            "resources": self.resources,
        }


@dataclass
class AdaptiveRoadmap:
    job_title: str
    current_score: int
    projected_score: int
    total_hours: int
    total_weeks: int
    hours_per_week: int
    immediate_actions: list[str] = field(default_factory=list)
    milestones: list[dict] = field(default_factory=list)
    tasks: list[AdaptiveTask] = field(default_factory=list)
    summary: str = ""
    ai_weekly_plan: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_title": self.job_title,
            "current_score": self.current_score,
            "projected_score": self.projected_score,
            "total_hours": self.total_hours,
            "total_weeks": self.total_weeks,
            "hours_per_week": self.hours_per_week,
            "immediate_actions": self.immediate_actions,
            "milestones": self.milestones,
            "tasks": [t.to_dict() for t in self.tasks],
            "summary": self.summary,
            "ai_weekly_plan": self.ai_weekly_plan,
        }


def _level(hours: int) -> str:
    return (SkillLevel.BEGINNER if hours <= 20
            else SkillLevel.INTERMEDIATE if hours <= 50
            else SkillLevel.ADVANCED).value


class AdaptiveRoadmapEngine:
    def build(self, *, skill_confidence: dict[str, float], target_skills: list[str],
              current_score: int, job_title: str,
              affinities: dict[str, float] | None = None,
              demand: dict[str, int] | None = None,
              hours_per_week: int = 10) -> AdaptiveRoadmap:
        affinities = affinities or {}
        demand = demand or {}
        hours_per_week = max(1, hours_per_week)
        conf = {k.lower(): v for k, v in skill_confidence.items()}

        items: list[AdaptiveTask] = []
        for skill in dict.fromkeys(s.lower() for s in target_skills):
            have = conf.get(skill, 0.0)
            if have >= _CONFIDENT:
                continue  # already competent → not in roadmap (progress-aware)
            kind = "reinforcement" if have > 0.0 else "gap"
            base_hours = SKILL_HOURS.get(skill, DEFAULT_HOURS)
            # reinforcement needs only the remaining fraction of effort
            est_hours = base_hours if kind == "gap" else max(4, int(base_hours * (1.0 - have)))
            dem = demand.get(skill, 1)
            aff = round(affinities.get(skill, 0.0), 3)
            quick_win = 8 if kind == "reinforcement" else 0
            priority_score = dem * 10 + aff * 5 + quick_win - est_hours / 20.0
            delta = (3 if kind == "reinforcement" else 5) + min(3, dem - 1)
            items.append(AdaptiveTask(
                skill=skill, kind=kind, priority=0, estimated_hours=est_hours,
                level=_level(est_hours), demand=dem, affinity=aff,
                score_delta=delta, week=0,
                resources=SKILL_RESOURCES.get(skill, DEFAULT_RESOURCES),
            ))

        items.sort(key=lambda t: (-(t.demand * 10 + t.affinity * 5
                                    + (8 if t.kind == "reinforcement" else 0)
                                    - t.estimated_hours / 20.0), t.estimated_hours))

        # schedule into weekly capacity + assign priority rank
        week, load = 1, 0
        for i, t in enumerate(items, 1):
            t.priority = i
            if load + t.estimated_hours > hours_per_week and load > 0:
                week += 1
                load = 0
            t.week = week
            load += t.estimated_hours

        total_hours = sum(t.estimated_hours for t in items)
        total_weeks = items[-1].week if items else 0
        projected = min(99, current_score + sum(t.score_delta for t in items))
        immediate = [t.skill for t in items[:3]]
        milestones = self._milestones(items, current_score)
        summary = (f"{len(items)} skills over ~{total_weeks} weeks "
                   f"({total_hours}h) to move {job_title} match {current_score} → {projected}."
                   if items else
                   f"No gaps — you already meet the confident-skill bar for {job_title}.")
        return AdaptiveRoadmap(
            job_title=job_title, current_score=current_score, projected_score=projected,
            total_hours=total_hours, total_weeks=total_weeks, hours_per_week=hours_per_week,
            immediate_actions=immediate, milestones=milestones, tasks=items, summary=summary,
        )

    async def build_ai(self, *, skill_confidence: dict[str, float], target_skills: list[str],
                       current_score: int, job_title: str, db, user_id: str,
                       affinities: dict[str, float] | None = None,
                       demand: dict[str, int] | None = None,
                       hours_per_week: int = 10) -> AdaptiveRoadmap:
        """Deterministic ``build`` enriched with an AI weekly study plan.

        The dependency ordering, scheduling, and — critically — the score
        projection all remain the deterministic engine's output (never the AI).
        The agent only supplies per-week activities/resources/tips, attached as
        ``ai_weekly_plan``. To stay token-efficient the agent receives only the
        missing skills + target role. Any failure or the toggle being off returns
        the deterministic roadmap unchanged.
        """
        roadmap = self.build(
            skill_confidence=skill_confidence, target_skills=target_skills,
            current_score=current_score, job_title=job_title,
            affinities=affinities, demand=demand, hours_per_week=hours_per_week,
        )
        if not settings.LLM_ENRICHMENT_ENABLED:
            logger.info("adaptive_roadmap_path", path="fallback", reason="disabled")
            return roadmap
        try:
            from app.agents.roadmap_agent import RoadmapAgent

            target_job = {
                "title": job_title,
                "required_skills": [t.skill for t in roadmap.tasks],
            }
            ai = await asyncio.wait_for(
                RoadmapAgent(db).generate(user_id, target_job, hours_per_week),
                timeout=settings.LLM_ENRICHMENT_TIMEOUT_SECONDS,
            )
            roadmap.ai_weekly_plan = [
                {
                    "week": w.number,
                    "skill": w.skill,
                    "topic": w.topic,
                    "hours": w.hours,
                    "activities": w.activities,
                    "checkpoint": w.checkpoint,
                }
                for w in (ai.weeks or [])
            ]
            logger.info(
                "adaptive_roadmap_path", path="ai_enriched",
                ai_weeks=len(roadmap.ai_weekly_plan),
            )
        except Exception as e:  # noqa: BLE001 — enrichment must never break the endpoint
            logger.warning("ai_enrichment_failed", module=__name__, error=str(e))
            return roadmap
        return roadmap

    @staticmethod
    def _milestones(items: list[AdaptiveTask], current_score: int) -> list[dict]:
        milestones: list[dict] = []
        running = current_score
        by_week: dict[int, list[AdaptiveTask]] = {}
        for t in items:
            by_week.setdefault(t.week, []).append(t)
        for wk in sorted(by_week):
            running = min(99, running + sum(t.score_delta for t in by_week[wk]))
            milestones.append({
                "week": wk,
                "skills": [t.skill for t in by_week[wk]],
                "projected_score": running,
            })
        return milestones


_default: AdaptiveRoadmapEngine | None = None


def get_adaptive_engine() -> AdaptiveRoadmapEngine:
    global _default
    if _default is None:
        _default = AdaptiveRoadmapEngine()
    return _default
