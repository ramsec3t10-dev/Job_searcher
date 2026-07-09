"""EMBEDHUNT AI — Long-term Memory Model.

Compact, importance-ranked memories that let the AI recall a candidate's
history (conversations, interviews, learning, applications) across sessions
without replaying full transcripts.
"""
from typing import Optional

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class MemoryEntry(BaseModel):
    __tablename__ = "memory_entries"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # conversation / interview / learning / resume / application / feedback
    memory_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # Claude-generated, <=500 tokens
    full_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importance_score: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1-5
    tags: Mapped[list] = mapped_column(JSON, default=list)  # skills, companies, etc.
    expires_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # null = permanent
    conversation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
