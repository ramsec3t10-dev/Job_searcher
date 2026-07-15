"""EMBEDHUNT AI — LLM conversation manager.

Persists per-conversation message history and, once a conversation grows long,
compresses it into a Haiku-generated summary to keep future prompts inside the
token budget.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.config.logging import get_logger
from app.config.settings import settings
from app.database.base import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.llm.router import AIRouter

logger = get_logger(__name__)


class Conversation(BaseModel):
    __tablename__ = "ai_conversations"
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ConversationManager:
    def __init__(self, router: "Optional[AIRouter]" = None, session_factory=None):
        self._router = router
        self._session_factory = session_factory

    def _sf(self):
        if self._session_factory is not None:
            return self._session_factory
        from app.database.session import AsyncSessionLocal

        return AsyncSessionLocal

    async def add_message(
        self, user_id: str, role: str, content: str, conversation_id: str, db: "Optional[AsyncSession]" = None
    ) -> Conversation:
        row = Conversation(user_id=user_id, conversation_id=conversation_id, role=role, content=content)
        if db is not None:
            db.add(row)
            await db.flush()
            return row
        async with self._sf()() as session:
            session.add(row)
            await session.commit()
        return row

    async def get_history(
        self, user_id: str, conversation_id: str, max_messages: int = 10, db: "Optional[AsyncSession]" = None
    ) -> list[dict]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.conversation_id == conversation_id,
                Conversation.role != "system",
            )
            .order_by(Conversation.created_at.desc())
            .limit(max_messages)
        )

        async def run(session) -> list[dict]:
            result = await session.execute(stmt)
            rows = list(reversed(result.scalars().all()))
            return [{"role": r.role, "content": r.content} for r in rows]

        if db is not None:
            return await run(db)
        async with self._sf()() as session:
            return await run(session)

    async def summarize_if_long(
        self,
        user_id: str,
        conversation_id: str,
        threshold: int = 20,
        db: "Optional[AsyncSession]" = None,
    ) -> Optional[str]:
        async def run(session) -> Optional[str]:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(Conversation)
                    .where(
                        Conversation.user_id == user_id,
                        Conversation.conversation_id == conversation_id,
                        Conversation.role != "system",
                    )
                )
            ).scalar_one()
            if count <= threshold or not settings.LLM_ENRICHMENT_ENABLED:
                return None
            rows = (
                await session.execute(
                    select(Conversation)
                    .where(
                        Conversation.user_id == user_id,
                        Conversation.conversation_id == conversation_id,
                        Conversation.role != "system",
                    )
                    .order_by(Conversation.created_at.asc())
                )
            ).scalars().all()
            transcript = "\n".join(f"{r.role}: {r.content}" for r in rows)
            # Phase 4: routes through the orchestrator (conversation_summarize
            # → open-model tier) instead of a direct Bedrock call.
            from app.orchestrator.router import get_orchestrator

            result = await get_orchestrator().handle(
                "conversation_summarize",
                {
                    "prompt": f"Summarize this conversation concisely, preserving key facts, "
                    f"preferences and decisions:\n\n{transcript}",
                    "system": "You are a precise conversation summarizer.",
                    "max_tokens": 512,
                },
                {"user_id": user_id, "db": session},
            )
            summary = result.text
            session.add(
                Conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role="system",
                    content="[summary]",
                    summary=summary,
                )
            )
            if db is not None:
                await session.flush()
            else:
                await session.commit()
            return summary

        if db is not None:
            return await run(db)
        async with self._sf()() as session:
            return await run(session)

    async def clear(self, user_id: str, conversation_id: str, db: "Optional[AsyncSession]" = None) -> None:
        stmt = delete(Conversation).where(
            Conversation.user_id == user_id, Conversation.conversation_id == conversation_id
        )
        if db is not None:
            await db.execute(stmt)
            await db.flush()
            return
        async with self._sf()() as session:
            await session.execute(stmt)
            await session.commit()
