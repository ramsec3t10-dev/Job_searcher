"""EMBEDHUNT AI — Interview Agent.

Generates company/skill-specific interview questions and evaluates answers.
Interview context is capped at 1500 tokens by the ContextBuilder; evaluations
feed back into the Career Twin and long-term memory.
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.agents.models import AnswerEvaluation, InterviewQuestion, QuestionList
from app.llm.context_builder import ContextBuilder
from app.llm.model_selector import TaskType
from app.llm.prompts import ANSWER_EVALUATOR, QUESTION_GENERATOR
from app.llm.response_parser import parse_structured


class InterviewAgent(BaseAgent):
    async def generate_questions(
        self, user_id: str, skill: str, company: str, difficulty: str, count: int = 5
    ) -> list[InterviewQuestion]:
        self.user_id = user_id
        twin = await self.twin_repo.get_by_user(user_id)
        # Context stays <=1500 tokens; used to steer difficulty to the candidate's level.
        ContextBuilder.for_interview(twin, {"company": company}, skill)
        user = QUESTION_GENERATOR.render(
            skill=skill, company=company, difficulty=difficulty, count=count
        )
        raw = await self._call(TaskType.INTERVIEW, QUESTION_GENERATOR.system_prompt, user, 2000)
        return parse_structured(raw, QuestionList).questions

    async def evaluate_answer(
        self, user_id: str, question: str, answer: str, skill: str
    ) -> AnswerEvaluation:
        self.user_id = user_id
        user = ANSWER_EVALUATOR.render(skill=skill, question=question, answer=answer)
        raw = await self._call(TaskType.INTERVIEW, ANSWER_EVALUATOR.system_prompt, user, 800)
        result: AnswerEvaluation = parse_structured(raw, AnswerEvaluation)

        # Fold the result back into the twin when one exists.
        if await self.twin_repo.get_by_user(user_id):
            await self.twin_service.update_after_interview(user_id, {
                "skill": skill,
                "score": result.score,
                "weak_topics": [skill] if result.what_was_missing else [],
                "notes": result.what_was_missing,
            })

        await self._store_memory(
            f"Interview {skill}: scored {result.score}/100. Weak: {result.what_was_missing[:100]}",
            "interview",
            importance=4,
            tags=[skill],
        )
        return result
