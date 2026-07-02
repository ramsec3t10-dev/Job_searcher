"""EMBEDHUNT AI — Feedback event repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.models.feedback import FeedbackEvent


class FeedbackEventRepository(BaseRepository[FeedbackEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, FeedbackEvent)

    async def list_for_user(self, user_id: str, limit: int = 500) -> list[FeedbackEvent]:
        r = await self.db.execute(
            select(FeedbackEvent).where(FeedbackEvent.user_id == user_id).limit(limit))
        return list(r.scalars().all())

    async def list_for_company(self, company: str, limit: int = 1000) -> list[FeedbackEvent]:
        r = await self.db.execute(
            select(FeedbackEvent).where(FeedbackEvent.company.ilike(company)).limit(limit))
        return list(r.scalars().all())
