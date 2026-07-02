"""EMBEDHUNT AI — Feedback API (learning loop)."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", status_code=201, summary="Record feedback on a job or recommendation")
async def record_feedback(
    payload: dict = Body(..., description="feedback_type + optional job_id, company, company_tier, skills, match_score, note"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    svc = FeedbackService(db)
    return await svc.record_feedback(
        user_id,
        payload.get("feedback_type", ""),
        job_id=payload.get("job_id", ""),
        company=payload.get("company", ""),
        company_tier=payload.get("company_tier", ""),
        skills=payload.get("skills"),
        match_score=int(payload.get("match_score", 0) or 0),
        note=payload.get("note"),
    )


@router.get("/affinities", summary="Learned skill and company affinities")
async def get_affinities(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await FeedbackService(db).get_affinities(user_id)


@router.get("/summary", summary="Feedback summary and preferences")
async def get_summary(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await FeedbackService(db).get_feedback_summary(user_id)
