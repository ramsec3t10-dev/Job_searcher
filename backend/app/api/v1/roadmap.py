"""EMBEDHUNT AI — Roadmap API"""
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.auth.permissions import get_current_user_id
from app.services.roadmap_service import RoadmapService
from app.services.adaptive_roadmap_service import AdaptiveRoadmapService

router = APIRouter(prefix="/roadmap", tags=["Learning Roadmap"])

@router.get("/", summary="General learning roadmap based on top matched jobs")
async def get_general(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await RoadmapService(db).get_general_roadmap(user_id)

@router.get("/job/{job_id}", summary="Roadmap for a specific job")
async def get_for_job(job_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await RoadmapService(db).get_roadmap_for_job(user_id, job_id)

@router.get("/adaptive/dream", summary="Adaptive roadmap toward the twin's dream companies")
async def adaptive_dream(hours_per_week: int = Query(10, ge=1, le=60), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await AdaptiveRoadmapService(db).roadmap_for_dream_companies(user_id, hours_per_week)

@router.post("/adaptive", summary="Adaptive roadmap toward a set of target skills")
async def adaptive_targets(payload: dict = Body(...), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await AdaptiveRoadmapService(db).roadmap_for_targets(
        user_id,
        target_skills=[s.strip().lower() for s in payload.get("target_skills", []) if s and s.strip()],
        job_title=payload.get("job_title", "Target Role"),
        hours_per_week=int(payload.get("hours_per_week", 10) or 10),
    )
