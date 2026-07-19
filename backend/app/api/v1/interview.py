"""EMBEDHUNT AI — Interview API"""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.auth.permissions import get_current_user_id
from app.services.interview_service import InterviewService
from app.services.mock_interview_service import MockInterviewService

router = APIRouter(prefix="/interview", tags=["Interview Preparation"])

@router.get("/prep", summary="General interview preparation kit")
async def general_prep(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await InterviewService(db).get_general_prep(user_id)

@router.get("/prep/{job_id}", summary="Interview kit for a specific job")
async def prep_for_job(job_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await InterviewService(db).get_interview_kit(user_id, job_id)

@router.post("/mock/generate", status_code=201, summary="Generate an adaptive mock interview")
async def generate_mock(payload: dict = Body(default={}), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    skills = payload.get("skills")
    return await MockInterviewService(db).generate(
        user_id,
        skills=[s.strip().lower() for s in skills] if skills else None,
        count=int(payload.get("count", 10) or 10),
        company=payload.get("company", ""),
        job_title=payload.get("job_title", "Mock Interview"),
        fmt=payload.get("format", "adaptive"),
    )

@router.post("/mock/{session_id}/evaluate", summary="Score mock interview answers")
async def evaluate_mock(session_id: str, payload: dict = Body(...), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await MockInterviewService(db).evaluate(user_id, session_id, payload.get("answers", {}))
