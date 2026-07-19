"""EMBEDHUNT AI — Domain Taxonomy Models (Phase 1 of multi-domain expansion).

Turns the platform's hardcoded "embedded engineering only" assumptions into
data. Each JobDomain owns weighted SkillCategories, which own Skills (with
aliases for synonym matching). Embedded engineering becomes Domain #1 of N —
its existing matcher weights are migrated into rows here unchanged, so nothing
about current behaviour shifts in this phase.
"""
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class JobDomain(BaseModel):
    """A node in the plug-and-play job taxonomy — a domain (level 0), sub-domain
    (level 1), or deeper. Self-referential via ``parent_id`` so arbitrary nesting
    needs no schema change. ``keywords`` are discriminative role/title terms the
    classifier's cheap rule tier matches before calling the LLM."""
    __tablename__ = "job_domains"

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Hierarchy (Phase 2) — additive on top of the Phase 1 flat table.
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("job_domains.id", ondelete="CASCADE"),
        nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class SkillCategory(BaseModel):
    """A weighted skill bucket within a domain (replaces the matcher's hardcoded
    WEIGHTS dict). ``weight`` is the category's contribution to the match score."""
    __tablename__ = "skill_categories"

    domain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_domains.id", ondelete="CASCADE"),
        nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=10, nullable=False)


class Skill(BaseModel):
    """A single skill inside a category, with aliases for synonym matching
    (e.g. "React.js" / "ReactJS" / "React")."""
    __tablename__ = "skills"

    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skill_categories.id", ondelete="CASCADE"),
        nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
