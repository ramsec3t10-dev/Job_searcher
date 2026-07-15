"""EMBEDHUNT AI — Resume Agent.

Parses, scores and rewrites resumes. Parsing is the only place the raw resume
text enters the pipeline; downstream agents read the Career Twin instead.
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.agents.models import ParsedResume, ResumeScore, RewrittenResume
from app.llm.context_builder import ContextBuilder
from app.llm.prompts import RESUME_PARSER, RESUME_REWRITER, RESUME_SCORER
from app.llm.response_parser import parse_structured
from app.models.career_twin import CareerTwin


class ResumeAgent(BaseAgent):
    async def parse(self, resume_text: str, user_id: str) -> ParsedResume:
        self.user_id = user_id
        context = ContextBuilder.for_resume_analysis(resume_text)
        user = RESUME_PARSER.render(resume_text=context["resume_text"])
        # Phase 4: orchestrator-routed (resume_parsing → open-model tier).
        raw = await self._handle("resume_parsing", RESUME_PARSER.system_prompt, user, 2000)
        result: ParsedResume = parse_structured(raw, ParsedResume)
        await self._store_memory(
            f"Resume parsed: {result.total_years}yr exp, {len(result.skills)} skills",
            "resume",
            importance=5,
            tags=result.skills[:10],
        )
        return result

    async def score(self, resume_text: str, job_description: str, user_id: str) -> ResumeScore:
        self.user_id = user_id
        user = RESUME_SCORER.render(job_description=job_description, resume_text=resume_text)
        # Phase 4: orchestrator-routed (resume_score → open-model tier).
        raw = await self._handle("resume_score", RESUME_SCORER.system_prompt, user, 1500)
        return parse_structured(raw, ResumeScore)

    async def rewrite(
        self, resume_text: str, job: dict, twin: CareerTwin, user_id: str
    ) -> RewrittenResume:
        self.user_id = user_id
        job_description = job.get("description", "") or job.get("title", "")
        user = RESUME_REWRITER.render(job_description=job_description, resume_text=resume_text)
        # Phase 4: orchestrator-routed (resume_rewrite → Claude tier).
        raw = await self._handle("resume_rewrite", RESUME_REWRITER.system_prompt, user, 1536)
        return parse_structured(raw, RewrittenResume)
