"""EMBEDHUNT AI — Knowledge Graph models.

A small directed graph of embedded-engineering skills plus role→skill
requirements. Powers deterministic (zero-LLM) answers to skill-prerequisite,
learning-path and role-requirement questions.

Edge direction convention: an edge ``from → to`` of type ``PREREQUISITE_OF``
means "``from`` is a prerequisite of ``to``" (learn ``from`` before ``to``), so
the seeded chain ``CAN → RTOS → MCAL → BSW → AUTOSAR → …`` reads as a learning
progression.
"""
from enum import Enum

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class EdgeType(str, Enum):
    PREREQUISITE_OF = "prerequisite_of"       # from is a prerequisite of to
    REQUIRED_BY = "required_by"               # from is required by to
    COMMONLY_PAIRED_WITH = "commonly_paired_with"  # skills usually learned together


class SkillNode(BaseModel):
    __tablename__ = "skill_nodes"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)


class SkillEdge(BaseModel):
    __tablename__ = "skill_edges"

    from_skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skill_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skill_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edge_type: Mapped[EdgeType] = mapped_column(
        SAEnum(EdgeType, name="skill_edge_type_enum"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("from_skill_id", "to_skill_id", "edge_type", name="uq_skill_edge"),
    )


class RoleRequirement(BaseModel):
    __tablename__ = "role_requirements"

    role_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("skill_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("role_name", "skill_id", name="uq_role_skill"),
    )
