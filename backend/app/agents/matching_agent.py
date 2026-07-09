"""EMBEDHUNT AI — Matching Agent.

Scores an embedded engineer's fit for a job and analyses skill gaps, always
reading from the Career Twin (never the raw resume) via the ContextBuilder.
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.agents.models import GapAnalysis, JobMatch
from app.llm.context_builder import ContextBuilder
from app.llm.model_selector import TaskType
from app.llm.prompts import GAP_ANALYSIS, JOB_MATCH
from app.llm.response_parser import parse_structured
from app.models.career_twin import CareerTwin


class MatchingAgent(BaseAgent):
    def _profile_and_job(self, context: dict, job: dict) -> tuple[str, str]:
        profile = self._json({
            "summary": context.get("candidate_summary", ""),
            "skills": context.get("skills", []),
            "experience_years": context.get("experience_years", 0),
            "current_role": context.get("current_role", ""),
        })
        job_str = self._json({
            "title": job.get("title", ""),
            "description": context.get("job_description", "") or job.get("description", ""),
            "required_skills": job.get("required_skills", []),
        })
        return profile, job_str

    async def match(self, twin: CareerTwin, job: dict, user_id: str) -> JobMatch:
        self.user_id = user_id
        context = ContextBuilder.for_job_matching(twin, job)
        profile, job_str = self._profile_and_job(context, job)
        user = JOB_MATCH.render(candidate_profile=profile, job=job_str)
        raw = await self._call(TaskType.MATCHING, JOB_MATCH.system_prompt, user, 1500)
        result: JobMatch = parse_structured(raw, JobMatch)
        await self._store_memory(
            f"Matched {job.get('title', 'job')}: score {result.score}, action {result.recommended_action}",
            "application",
            importance=3,
            tags=result.missing_skills[:5],
        )
        return result

    async def analyze_gaps(self, twin: CareerTwin, job: dict, user_id: str) -> GapAnalysis:
        self.user_id = user_id
        context = ContextBuilder.for_job_matching(twin, job)
        profile, job_str = self._profile_and_job(context, job)
        user = GAP_ANALYSIS.render(candidate_profile=profile, job=job_str)
        raw = await self._call(TaskType.MATCHING, GAP_ANALYSIS.system_prompt, user, 1024)
        return parse_structured(raw, GapAnalysis)
