"""EMBEDHUNT AI — Learning Agent.

Produces bite-sized teaching content: full lessons (with quiz) and
spaced-repetition flashcards for a given skill.
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.agents.models import Flashcard, FlashcardList, Lesson
from app.llm.prompts import FLASHCARD_GENERATOR, LESSON_GENERATOR
from app.llm.response_parser import parse_structured


class LearningAgent(BaseAgent):
    async def create_lesson(self, user_id: str, skill: str, topic: str) -> Lesson:
        self.user_id = user_id
        twin = await self.twin_repo.get_by_user(user_id)
        level = getattr(twin, "career_level", None) or "intermediate"
        user = LESSON_GENERATOR.render(skill=skill, topic=topic, level=level)
        # Phase 4: orchestrator-routed (lesson_generation → open-model tier).
        raw = await self._handle("lesson_generation", LESSON_GENERATOR.system_prompt, user, 2000)
        return parse_structured(raw, Lesson)

    async def create_flashcards(self, user_id: str, skill: str, count: int = 10) -> list[Flashcard]:
        self.user_id = user_id
        user = FLASHCARD_GENERATOR.render(skill=skill, topic=skill, count=count)
        # Phase 4: orchestrator-routed (flashcard_generation → open-model tier).
        raw = await self._handle("flashcard_generation", FLASHCARD_GENERATOR.system_prompt, user, 1500)
        return parse_structured(raw, FlashcardList).cards
