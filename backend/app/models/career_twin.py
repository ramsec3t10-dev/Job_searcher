"""EMBEDHUNT AI — Career Twin Model (living, versioned source of truth)."""
from typing import Optional
from sqlalchemy import String, Boolean, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import BaseModel


class CareerTwin(BaseModel):
    __tablename__ = "career_twins"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    last_synced_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Identity
    full_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    linkedin_url: Mapped[str] = mapped_column(String(500), default="")
    github_url: Mapped[str] = mapped_column(String(500), default="")

    # Skills with confidence — list[{name, category, confidence, depth, years_used,
    # recency_score, last_used_year, source}]
    skills: Mapped[list] = mapped_column(JSON, default=list)

    # Experience timeline
    experience_entries: Mapped[list] = mapped_column(JSON, default=list)

    # Career metrics
    total_years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    current_role: Mapped[str] = mapped_column(String(200), default="")
    current_company: Mapped[str] = mapped_column(String(200), default="")
    current_salary_lpa: Mapped[float] = mapped_column(Float, default=0.0)
    target_salary_lpa: Mapped[float] = mapped_column(Float, default=0.0)
    career_level: Mapped[str] = mapped_column(String(30), default="junior")
    career_trajectory: Mapped[str] = mapped_column(String(30), default="stable")

    # Intelligence scores
    embedded_domain_score: Mapped[int] = mapped_column(Integer, default=0)
    profile_completeness: Mapped[int] = mapped_column(Integer, default=0)
    interview_readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    market_value_score: Mapped[int] = mapped_column(Integer, default=0)
    learning_velocity: Mapped[float] = mapped_column(Float, default=0.0)

    # Preferences
    dream_companies: Mapped[list] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[list] = mapped_column(JSON, default=list)
    preferred_domains: Mapped[list] = mapped_column(JSON, default=list)
    work_mode_preference: Mapped[str] = mapped_column(String(20), default="hybrid")
    min_salary_lpa: Mapped[float] = mapped_column(Float, default=0.0)
    open_to_relocation: Mapped[bool] = mapped_column(Boolean, default=True)

    # Education / certifications / projects / publications
    education_entries: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    publications: Mapped[list] = mapped_column(JSON, default=list)

    # Interview history
    interview_history: Mapped[list] = mapped_column(JSON, default=list)

    # Personality / style
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    known_weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    interview_style_notes: Mapped[str] = mapped_column(String(1000), default="")

    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_resume_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    last_resume_parse_date: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Per-field change log: {field_name: iso_timestamp} — powers weekly delta.
    change_log: Mapped[dict] = mapped_column(JSON, default=dict)

    # ── Long-term memory / goals (Phase 3, additive) ──────────────────────
    career_goals: Mapped[dict] = mapped_column(JSON, default=dict)  # {short_term, long_term, target_role}
    learning_style: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # visual/reading/practice
    interviews_completed: Mapped[int] = mapped_column(Integer, default=0)
    avg_interview_score: Mapped[float] = mapped_column(Float, default=0.0)
    weak_interview_topics: Mapped[list] = mapped_column(JSON, default=list)
    skills_learned_this_month: Mapped[list] = mapped_column(JSON, default=list)
    learning_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
