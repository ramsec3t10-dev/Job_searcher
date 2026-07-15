"""EMBEDHUNT AI — Coding Agent.

Reviews embedded C/C++ code (correctness, MISRA, memory, concurrency) and
authors self-contained coding challenges. Deliberately token-lean: only the
code and skill are sent, never the full Career Twin.
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.agents.models import CodeReview, CodingChallenge
from app.llm.prompts import CHALLENGE_GENERATOR, CODE_REVIEWER
from app.llm.response_parser import parse_structured


class CodingAgent(BaseAgent):
    async def review_code(self, user_id: str, code: str, language: str = "c") -> CodeReview:
        self.user_id = user_id
        user = CODE_REVIEWER.render(language=language, context="", code=code)
        # Phase 4: orchestrator-routed (coding_review_explanation → open-model tier).
        raw = await self._handle("coding_review_explanation", CODE_REVIEWER.system_prompt, user, 1500)
        return parse_structured(raw, CodeReview)

    async def generate_challenge(
        self, user_id: str, skill: str, difficulty: str
    ) -> CodingChallenge:
        self.user_id = user_id
        user = CHALLENGE_GENERATOR.render(skill=skill, difficulty=difficulty, focus=skill)
        # Phase 4: orchestrator-routed (coding_challenge → open-model tier).
        raw = await self._handle("coding_challenge", CHALLENGE_GENERATOR.system_prompt, user, 2000)
        return parse_structured(raw, CodingChallenge)
