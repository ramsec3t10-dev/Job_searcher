"""EMBEDHUNT AI — Weekly Career Report API (Module 14)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.services.weekly_report_service import WeeklyReportService

router = APIRouter(prefix="/report", tags=["Weekly Report"])


@router.get("/weekly", summary="Generate this week's career report")
async def weekly_report(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await WeeklyReportService(db).generate(user_id)
