"""EMBEDHUNT AI — Roadmap Agent.

Builds a week-by-week upskilling plan from the Career Twin's gaps toward a
target role, respecting available hours and learning velocity.
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.agents.models import Roadmap
from app.llm.context_builder import ContextBuilder
from app.llm.model_selector import TaskType
from app.llm.prompts import ROADMAP_GENERATOR
from app.llm.response_parser import parse_structured


class RoadmapAgent(BaseAgent):
    async def generate(self, user_id: str, target_job: dict, hours_per_week: int) -> Roadmap:
        self.user_id = user_id
        twin = await self.twin_repo.get_by_user(user_id)
        context = ContextBuilder.for_roadmap(twin, target_job, hours_per_week)

        career_twin = self._json({
            "current_skills": context.get("current_skills", []),
            "missing_skills": context.get("missing_skills", []),
            "experience_level": context.get("experience_level", ""),
        })
        interview_history = self._json(getattr(twin, "interview_history", None) or [])

        user = ROADMAP_GENERATOR.render(
            target_role=context.get("target_role", "") or target_job.get("title", ""),
            hours_per_week=hours_per_week,
            learning_velocity=context.get("learning_velocity", 0.0),
            career_twin=career_twin,
            interview_history=interview_history,
        )
        raw = await self._call(TaskType.ROADMAP, ROADMAP_GENERATOR.system_prompt, user, 3000)
        result: Roadmap = parse_structured(raw, Roadmap)
        await self._store_memory(
            f"Roadmap: {result.total_weeks}wk plan for {target_job.get('title')}",
            "learning",
            importance=3,
            tags=[],
        )
        return result
