"""EMBEDHUNT AI — Daily Coach API."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.services.daily_coach_service import DailyCoachService

router = APIRouter(prefix="/coach", tags=["Daily Coach"])


@router.get("/today", summary="Personalised daily coaching brief")
async def today(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await DailyCoachService(db).get_daily_brief(user_id)


@router.post("/checkin", status_code=201, summary="Record a daily check-in (streak)")
async def checkin(payload: dict = Body(default={}), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await DailyCoachService(db).check_in(
        user_id,
        tasks_completed=int(payload.get("tasks_completed", 0) or 0),
        note=payload.get("note"),
    )
