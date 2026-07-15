"""EMBEDHUNT AI — Salary Agent.

Estimates market compensation (in LPA) for the candidate from their Career Twin
and location, optionally anchored to a target company.
"""
from __future__ import annotations

from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.models import SalaryEstimate
from app.llm.context_builder import ContextBuilder
from app.llm.prompts import SALARY_ESTIMATOR
from app.llm.response_parser import parse_structured


class SalaryAgent(BaseAgent):
    async def estimate(self, user_id: str, target_company: Optional[str] = None) -> SalaryEstimate:
        self.user_id = user_id
        twin = await self.twin_repo.get_by_user(user_id)
        context = ContextBuilder.for_salary(twin, target_company)

        profile = self._json({
            "skills": context.get("skills", []),
            "experience_years": context.get("experience_years", 0),
            "level": context.get("level", ""),
            "target_company": context.get("target_company", ""),
        })
        user = SALARY_ESTIMATOR.render(
            location=context.get("location", ""),
            current_lpa=context.get("current_salary", 0.0),
            profile=profile,
        )
        # Phase 4: orchestrator-routed (salary_estimate → Claude tier, money advice).
        raw = await self._handle("salary_estimate", SALARY_ESTIMATOR.system_prompt, user, 800)
        return parse_structured(raw, SalaryEstimate)
