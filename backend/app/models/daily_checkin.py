"""EMBEDHUNT AI — Daily coach check-in model (streak tracking)."""
from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class DailyCheckin(BaseModel):
    __tablename__ = "daily_checkins"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    checkin_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
