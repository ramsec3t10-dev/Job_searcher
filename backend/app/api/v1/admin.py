"""EMBEDHUNT AI — Admin observability endpoints (platform-admin only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import UserRole, require_min_role
from app.database.session import get_db
from app.repositories.ai_usage_repository import AiUsageRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ai-usage", dependencies=[Depends(require_min_role(UserRole.PLATFORM_ADMIN))])
async def ai_usage(db: AsyncSession = Depends(get_db)) -> dict:
    """AI cost & routing distribution for the current month.

    Returns total cost, cost/latency/percentage by engine tier
    (rule/kg/cache/hosted/claude) — the "% to Claude" launch KPI — and the top
    10 highest-cost task types. Sourced directly from ``AiUsageLog``.
    """
    return await AiUsageRepository(db).monthly_summary()
