"""EMBEDHUNT AI — Curated interview question bank (Phase 7).

A domain- and subrole-scoped store of real interview questions. Subrole is a
plain string key (e.g. "backend_engineer", "sales_executive") that matches the
values shipped in the per-subrole data files — deliberately NOT a new FK table,
so new subroles arrive as data without a schema change.

``model_answer_guideline`` describes what a strong answer covers — it is a
guideline, not a scripted answer to memorize.
"""
from enum import Enum
from typing import Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class QuestionCategory(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CASE_STUDY = "case_study"
    SYSTEM_DESIGN = "system_design"


class QuestionDifficulty(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


class QuestionSource(str, Enum):
    CURATED = "curated"
    GENERATED = "generated"


class InterviewQuestion(BaseModel):
    __tablename__ = "interview_questions"

    domain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_domains.id", ondelete="CASCADE"),
        nullable=False, index=True)
    subrole_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[QuestionCategory] = mapped_column(
        SAEnum(QuestionCategory, name="interview_question_category_enum"),
        nullable=False, index=True)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        SAEnum(QuestionDifficulty, name="interview_question_difficulty_enum"),
        nullable=False, index=True)
    model_answer_guideline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[QuestionSource] = mapped_column(
        SAEnum(QuestionSource, name="interview_question_source_enum"),
        default=QuestionSource.CURATED, nullable=False)
