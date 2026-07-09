"""EMBEDHUNT AI — Agent response models.

Typed Pydantic models for every structured agent output. Each model mirrors the
JSON shape declared in the corresponding prompt's system instruction. Fields
carry safe defaults so a partial model response still validates.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── Resume ────────────────────────────────────────────────────────────────
class Experience(_Base):
    company: str = ""
    title: str = ""
    years: float = 0.0
    highlights: list[str] = Field(default_factory=list)


class Education(_Base):
    degree: str = ""
    institution: str = ""
    year: int = 0


class Project(_Base):
    name: str = ""
    description: str = ""


class Contact(_Base):
    name: str = ""
    email: str = ""
    phone: str = ""


class ParsedResume(_Base):
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    contact: Contact = Field(default_factory=Contact)
    summary: str = ""
    total_years: float = 0.0


class ResumeScore(_Base):
    score: int = 0
    ats_score: int = 0
    missing_keywords: list[str] = Field(default_factory=list)
    weak_bullets: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)


class RewrittenResume(_Base):
    rewritten_bullets: list[str] = Field(default_factory=list)
    summary: str = ""
    keywords_added: list[str] = Field(default_factory=list)
    estimated_score_improvement: int = 0


# ── Matching ──────────────────────────────────────────────────────────────
class JobMatch(_Base):
    score: int = 0
    reasoning: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    interview_probability: int = 0
    salary_confidence: int = 0
    growth_potential: str = ""
    recommended_action: str = ""


class GapAnalysis(_Base):
    critical_gaps: list[str] = Field(default_factory=list)
    nice_to_have_gaps: list[str] = Field(default_factory=list)
    estimated_upskill_weeks: int = 0
    learning_priority: list[str] = Field(default_factory=list)
    immediate_focus: str = ""
    gap_summary: str = ""


# ── Mentor ────────────────────────────────────────────────────────────────
class MentorResponse(_Base):
    advice: str = ""
    action_items: list[str] = Field(default_factory=list)
    priority: str = "medium"
    timeframe: str = ""


class BriefItem(_Base):
    emoji: str = ""
    text: str = ""
    action_route: str = ""


class DailyBrief(_Base):
    greeting: str = ""
    focus_skill: str = ""
    reason: str = ""
    new_jobs_count: int = 0
    top_action: str = ""
    motivational_note: str = ""
    items: list[BriefItem] = Field(default_factory=list)


# ── Interview ─────────────────────────────────────────────────────────────
class InterviewQuestion(_Base):
    text: str = ""
    type: str = ""
    difficulty: str = ""
    expected_answer_outline: str = ""
    follow_up: str = ""
    company_tags: list[str] = Field(default_factory=list)


class QuestionList(_Base):
    questions: list[InterviewQuestion] = Field(default_factory=list)


class AnswerEvaluation(_Base):
    score: int = 0
    technical_accuracy: int = 0
    communication: int = 0
    depth: int = 0
    feedback: str = ""
    what_was_good: str = ""
    what_was_missing: str = ""
    follow_up_question: str = ""


# ── Roadmap ───────────────────────────────────────────────────────────────
class RoadmapWeek(_Base):
    number: int = 0
    skill: str = ""
    topic: str = ""
    hours: int = 0
    activities: list[str] = Field(default_factory=list)
    checkpoint: str = ""
    projected_score: int = 0


class Roadmap(_Base):
    weeks: list[RoadmapWeek] = Field(default_factory=list)
    total_weeks: int = 0
    career_path: str = ""
    summary: str = ""


# ── Salary ────────────────────────────────────────────────────────────────
class SalaryEstimate(_Base):
    estimated_min_lpa: float = 0.0
    estimated_max_lpa: float = 0.0
    percentile: int = 0
    is_underpaid: bool = False
    underpaid_by: float = 0.0
    top_skills_for_raise: list[str] = Field(default_factory=list)
    negotiation_tips: list[str] = Field(default_factory=list)
    market_reasoning: str = ""


# ── Learning ──────────────────────────────────────────────────────────────
class QuizItem(_Base):
    question: str = ""
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    explanation: str = ""


class Lesson(_Base):
    topic: str = ""
    explanation: str = ""
    key_concepts: list[str] = Field(default_factory=list)
    practical_example: str = ""
    code_snippet: str = ""
    quiz: list[QuizItem] = Field(default_factory=list)


class Flashcard(_Base):
    front: str = ""
    back: str = ""
    difficulty: str = ""
    tags: list[str] = Field(default_factory=list)


class FlashcardList(_Base):
    cards: list[Flashcard] = Field(default_factory=list)


# ── Coding ────────────────────────────────────────────────────────────────
class MisraViolation(_Base):
    rule: str = ""
    line: int = 0
    description: str = ""


class CodeReview(_Base):
    overall_score: int = 0
    misra_violations: list[MisraViolation] = Field(default_factory=list)
    memory_issues: list[str] = Field(default_factory=list)
    concurrency_issues: list[str] = Field(default_factory=list)
    style_issues: list[str] = Field(default_factory=list)
    positive_aspects: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class TestCase(_Base):
    input: str = ""
    expected: str = ""


class CodingChallenge(_Base):
    title: str = ""
    description: str = ""
    starter_code: str = ""
    test_cases: list[TestCase] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    reference_solution: str = ""
    skills_tested: list[str] = Field(default_factory=list)
    difficulty: str = ""
