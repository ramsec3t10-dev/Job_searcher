"""EMBEDHUNT AI — Discovered Job model (persisted live-pipeline corpus)."""
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class DiscoveredJob(BaseModel):
    __tablename__ = "discovered_jobs"

    # stable per-source identity: "{source_portal}:{external_id}"
    external_ref: Mapped[str] = mapped_column(String(300), nullable=False, unique=True, index=True)
    dedup_key: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    # Multi-domain (Phase 1): every posting is domain-tagged; existing rows
    # backfilled to embedded_engineering by the data migration.
    domain_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("job_domains.id"), nullable=True, index=True)
    # Company/posting industry when the source provides it (Phase 2). Distinct
    # from domain_id: a software company can post a sales role.
    industry: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    company_tier: Mapped[str] = mapped_column(String(50), default="other")
    location: Mapped[str] = mapped_column(String(200), default="")
    source_portal: Mapped[str] = mapped_column(String(100), default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    apply_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[str] = mapped_column(Text, default="")

    experience_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_min_lpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max_lpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_corpus_dict(self) -> dict:
        return {
            "id": self.external_ref,
            "title": self.title,
            "company": self.company,
            "company_tier": self.company_tier,
            "location": self.location,
            "source_portal": self.source_portal,
            "source_url": self.source_url,
            "apply_url": self.apply_url,
            "description": self.description,
            "required_skills": self.required_skills,
            "experience_min": self.experience_min,
            "experience_max": self.experience_max,
            "salary_min_lpa": self.salary_min_lpa,
            "salary_max_lpa": self.salary_max_lpa,
        }
