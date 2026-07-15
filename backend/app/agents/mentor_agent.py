"""EMBEDHUNT AI — Mentor Agent.

Conversational career mentor grounded in the Career Twin plus long-term memory.
Loads at most 8 memory entries to stay token-efficient, and persists both the
turn (conversation history) and a compact memory of the advice given.
"""
from __future__ import annotations

import asyncio
from datetime import date

from app.agents.base_agent import BaseAgent
from app.agents.models import DailyBrief, MentorResponse
from app.llm.context_builder import ContextBuilder
from app.llm.prompts import CAREER_ADVICE, DAILY_BRIEF
from app.llm.response_parser import parse_structured


class MentorAgent(BaseAgent):
    async def advise(self, user_id: str, message: str, conversation_id: str) -> MentorResponse:
        self.user_id = user_id
        # Twin and long-term memory are independent reads — fetch in parallel.
        twin, memories = await asyncio.gather(
            self.twin_repo.get_by_user(user_id),
            self.memory_repo.get_relevant(
                user_id, tags=["conversation", "interview", "learning"], limit=8
            ),
        )
        context = ContextBuilder.for_career_mentor(twin, memories, message, user_id=user_id)
        history = await self.conversation_manager.get_history(user_id, conversation_id, db=self.db)

        history_text = context["recent_history"]
        if history:
            history_text += "\n" + "\n".join(f"{h['role']}: {h['content']}" for h in history)
        goals = self._json(getattr(twin, "career_goals", None) or {})

        user = CAREER_ADVICE.render(
            career_twin=context["candidate_context"],
            history=history_text,
            goals=goals,
            question=message,
        )
        await self.conversation_manager.add_message(user_id, "user", message, conversation_id, db=self.db)
        # Phase 4: routed through the orchestrator (mentor_chat → Claude tier).
        raw = await self._handle("mentor_chat", CAREER_ADVICE.system_prompt, user, 1000)
        result: MentorResponse = parse_structured(raw, MentorResponse)

        await self.conversation_manager.add_message(
            user_id, "assistant", result.advice, conversation_id, db=self.db
        )
        await self._store_memory(f"Advice: {result.advice[:200]}", "conversation", 2, [])
        return result

    async def daily_brief(self, user_id: str) -> DailyBrief:
        self.user_id = user_id
        twin = await self.twin_repo.get_by_user(user_id)
        context = ContextBuilder.for_career_mentor(twin, [], "", user_id=user_id)
        weak = getattr(twin, "weak_interview_topics", None) or getattr(twin, "known_weaknesses", None) or []
        top_gap = weak[0] if weak else ""

        user = DAILY_BRIEF.render(
            date=date.today().isoformat(),
            new_jobs_count=0,
            top_gap=top_gap,
            career_twin=context["candidate_context"],
        )
        # Phase 4: routed through the orchestrator (mentor_daily_brief → open-model tier).
        raw = await self._handle("mentor_daily_brief", DAILY_BRIEF.system_prompt, user, 1000)
        return parse_structured(raw, DailyBrief)
