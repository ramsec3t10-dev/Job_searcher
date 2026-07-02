"""EMBEDHUNT AI — Feedback event model (learning loop)."""
from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum

from app.database.base import BaseModel


class FeedbackType(str, Enum):
    SAVED = "saved"
    DISMISSED = "dismissed"
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    GHOSTED = "ghosted"
    REC_POSITIVE = "rec_positive"
    REC_NEGATIVE = "rec_negative"


class FeedbackEvent(BaseModel):
    __tablename__ = "feedback_events"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(200), default="", index=True)
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)
    signal: Mapped[float] = mapped_column(Float, default=0.0)
    company: Mapped[str] = mapped_column(String(200), default="")
    company_tier: Mapped[str] = mapped_column(String(50), default="")
    skills: Mapped[str] = mapped_column(Text, default="")  # csv of job skills
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
