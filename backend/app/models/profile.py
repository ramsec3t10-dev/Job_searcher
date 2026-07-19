"""EMBEDHUNT AI — Candidate Profile Model"""
from typing import Optional
from sqlalchemy import String, Boolean, Text, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import BaseModel

class CandidateProfile(BaseModel):
    __tablename__ = "candidate_profiles"
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(300), default="Embedded Software Engineer")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ── Multi-domain (Phase 1) — additive; embedded columns above stay authoritative
    # for existing code paths until later phases read from domain_profile_data. ──
    primary_domain_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("job_domains.id"), nullable=True, index=True)
    secondary_domain_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    domain_profile_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    total_experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    current_role: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    current_company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Skills (from resume AI pipeline)
    skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON list
    profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # Full CandidateProfile JSON
    embedded_domain_score: Mapped[int] = mapped_column(Integer, default=0)
    profile_score: Mapped[int] = mapped_column(Integer, default=0)              # Overall 0-100
    # Preferences
    is_actively_looking: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    min_salary_lpa: Mapped[float] = mapped_column(Float, default=15.0)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=60)
    # Education
    highest_degree: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # AI feedback tracking
    total_recommendations: Mapped[int] = mapped_column(Integer, default=0)
    total_applications: Mapped[int] = mapped_column(Integer, default=0)
    interview_rate: Mapped[float] = mapped_column(Float, default=0.0)
    offer_rate: Mapped[float] = mapped_column(Float, default=0.0)
