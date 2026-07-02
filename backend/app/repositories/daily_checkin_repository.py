"""EMBEDHUNT AI — Daily check-in repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.models.daily_checkin import DailyCheckin


class DailyCheckinRepository(BaseRepository[DailyCheckin]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, DailyCheckin)

    async def get_for_date(self, user_id: str, checkin_date: str) -> DailyCheckin | None:
        r = await self.db.execute(
            select(DailyCheckin).where(
                DailyCheckin.user_id == user_id,
                DailyCheckin.checkin_date == checkin_date,
            ))
        return r.scalar_one_or_none()

    async def list_dates(self, user_id: str, limit: int = 400) -> list[str]:
        r = await self.db.execute(
            select(DailyCheckin.checkin_date).where(DailyCheckin.user_id == user_id).limit(limit))
        return [row[0] for row in r.all()]
