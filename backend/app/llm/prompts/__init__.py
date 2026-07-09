"""EMBEDHUNT AI — Prompt library.

Every prompt is a typed PromptTemplate exported by name. ALL_PROMPTS maps each
template name to its instance for iteration (validation, catalogs, routing).
"""
from app.llm.prompts.base import PromptTemplate
from app.llm.prompts.coding_prompts import CHALLENGE_GENERATOR, CODE_REVIEWER
from app.llm.prompts.company_prompts import COMPANY_INTELLIGENCE
from app.llm.prompts.interview_prompts import (
    ANSWER_EVALUATOR,
    MOCK_INTERVIEW_OPENER,
    QUESTION_GENERATOR,
)
from app.llm.prompts.learning_prompts import FLASHCARD_GENERATOR, LESSON_GENERATOR
from app.llm.prompts.matching_prompts import GAP_ANALYSIS, JOB_MATCH
from app.llm.prompts.mentor_prompts import CAREER_ADVICE, DAILY_BRIEF
from app.llm.prompts.resume_prompts import (
    RESUME_PARSER,
    RESUME_REWRITER,
    RESUME_SCORER,
)
from app.llm.prompts.roadmap_prompts import ROADMAP_GENERATOR, WEEK_PLANNER
from app.llm.prompts.salary_prompts import SALARY_ESTIMATOR

ALL_PROMPTS: dict[str, PromptTemplate] = {
    "RESUME_PARSER": RESUME_PARSER,
    "RESUME_SCORER": RESUME_SCORER,
    "RESUME_REWRITER": RESUME_REWRITER,
    "JOB_MATCH": JOB_MATCH,
    "GAP_ANALYSIS": GAP_ANALYSIS,
    "CAREER_ADVICE": CAREER_ADVICE,
    "DAILY_BRIEF": DAILY_BRIEF,
    "QUESTION_GENERATOR": QUESTION_GENERATOR,
    "ANSWER_EVALUATOR": ANSWER_EVALUATOR,
    "MOCK_INTERVIEW_OPENER": MOCK_INTERVIEW_OPENER,
    "ROADMAP_GENERATOR": ROADMAP_GENERATOR,
    "WEEK_PLANNER": WEEK_PLANNER,
    "SALARY_ESTIMATOR": SALARY_ESTIMATOR,
    "LESSON_GENERATOR": LESSON_GENERATOR,
    "FLASHCARD_GENERATOR": FLASHCARD_GENERATOR,
    "CODE_REVIEWER": CODE_REVIEWER,
    "CHALLENGE_GENERATOR": CHALLENGE_GENERATOR,
    "COMPANY_INTELLIGENCE": COMPANY_INTELLIGENCE,
}

__all__ = [
    "PromptTemplate",
    "ALL_PROMPTS",
    "RESUME_PARSER",
    "RESUME_SCORER",
    "RESUME_REWRITER",
    "JOB_MATCH",
    "GAP_ANALYSIS",
    "CAREER_ADVICE",
    "DAILY_BRIEF",
    "QUESTION_GENERATOR",
    "ANSWER_EVALUATOR",
    "MOCK_INTERVIEW_OPENER",
    "ROADMAP_GENERATOR",
    "WEEK_PLANNER",
    "SALARY_ESTIMATOR",
    "LESSON_GENERATOR",
    "FLASHCARD_GENERATOR",
    "CODE_REVIEWER",
    "CHALLENGE_GENERATOR",
    "COMPANY_INTELLIGENCE",
]
