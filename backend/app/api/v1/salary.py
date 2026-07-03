"""EMBEDHUNT AI — Salary Intelligence API (Module 12)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.services.salary_service import SalaryService

router = APIRouter(prefix="/salary", tags=["Salary Intelligence"])


@router.get("/intelligence", summary="Market-value estimate for the candidate")
async def salary_intelligence(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await SalaryService(db).get_intelligence(user_id)


@router.get("/negotiation-brief", summary="Actionable salary-negotiation brief")
async def negotiation_brief(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await SalaryService(db).negotiation_brief(user_id)
