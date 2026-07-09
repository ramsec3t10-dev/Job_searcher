"""EMBEDHUNT AI — Long-term Memory Repository.

Stores importance-ranked memories and retrieves the most relevant ones for a
given context. Old, low-value memories are periodically compressed into shorter
summaries using the cheapest model (Haiku) to keep recall cheap.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.models.memory import MemoryEntry

logger = get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryRepository:
    """Data + retrieval layer for :class:`MemoryEntry`.

    ``router`` is optional; when absent, :meth:`summarize_old` is a safe no-op so
    the repository works in environments without LLM access (e.g. unit tests).
    """

    def __init__(self, db: AsyncSession, router=None):
        self.db = db
        self.router = router

    async def store(
        self,
        user_id: str,
        memory_type: str,
        summary: str,
        *,
        full_content: Optional[str] = None,
        importance_score: int = 3,
        tags: Optional[list[str]] = None,
        expires_at: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            user_id=user_id,
            memory_type=memory_type,
            summary=summary,
            full_content=full_content,
            importance_score=max(1, min(5, importance_score)),
            tags=tags or [],
            expires_at=expires_at,
            conversation_id=conversation_id,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_relevant(
        self,
        user_id: str,
        *,
        tags: Optional[list[str]] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Return the most important non-expired memories matching the filters.

        Keyword relevance is approximated by tag overlap; ranking is by
        ``importance_score`` then recency. (Vector search can replace this later
        without changing the interface.)
        """
        stmt = select(MemoryEntry).where(MemoryEntry.user_id == user_id)
        if memory_type:
            stmt = stmt.where(MemoryEntry.memory_type == memory_type)
        result = await self.db.execute(stmt)
        rows = [m for m in result.scalars().all() if not self._expired(m)]

        wanted = {t.lower() for t in (tags or [])}
        def score(m: MemoryEntry) -> tuple:
            overlap = len(wanted & {t.lower() for t in (m.tags or [])}) if wanted else 0
            return (overlap, m.importance_score or 0, m.created_at or datetime.min)
        rows.sort(key=score, reverse=True)
        return rows[:limit]

    async def get_recent(
        self,
        user_id: str,
        *,
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        stmt = select(MemoryEntry).where(MemoryEntry.user_id == user_id)
        if memory_type:
            stmt = stmt.where(MemoryEntry.memory_type == memory_type)
        stmt = stmt.order_by(MemoryEntry.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def summarize_old(self, user_id: str, *, older_than_days: int = 30) -> int:
        """Compress low-importance memories older than ``older_than_days``.

        Uses the SUMMARIZATION task (routes to Haiku). Returns the number of
        memories compressed. No-op if no router is configured.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.user_id == user_id)
        )
        stale = [
            m for m in result.scalars().all()
            if m.created_at and m.created_at.replace(tzinfo=timezone.utc) < cutoff
            and m.full_content and (m.importance_score or 0) <= 3
        ]
        if not stale or self.router is None:
            return 0

        from app.llm.model_selector import TaskType

        compressed = 0
        for m in stale:
            try:
                resp = await self.router.route(
                    TaskType.SUMMARIZATION,
                    messages=[{
                        "role": "user",
                        "content": f"Summarize this memory in one sentence:\n\n{m.full_content}",
                    }],
                    system="You compress career-history notes into a single concise sentence.",
                    max_tokens=120,
                    user_id=user_id,
                )
                m.summary = resp.content.strip()
                m.full_content = None  # drop the bulky original
                compressed += 1
            except Exception:  # pragma: no cover - defensive; never fail a cron job
                logger.warning("memory_summarize_failed", memory_id=m.id)
        await self.db.flush()
        return compressed

    async def delete_expired(self) -> int:
        result = await self.db.execute(select(MemoryEntry).where(MemoryEntry.expires_at.isnot(None)))
        expired = [m for m in result.scalars().all() if self._expired(m)]
        for m in expired:
            await self.db.delete(m)
        await self.db.flush()
        return len(expired)

    @staticmethod
    def _expired(m: MemoryEntry) -> bool:
        if not m.expires_at:
            return False
        try:
            return datetime.fromisoformat(m.expires_at) < datetime.now(timezone.utc)
        except ValueError:
            return False
