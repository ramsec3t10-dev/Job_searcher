"""EMBEDHUNT AI — Resume API"""
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.auth.permissions import get_current_user_id
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["Resume Intelligence"])

@router.post("/upload", status_code=201, summary="Upload + parse + profile a resume")
async def upload(
    file: UploadFile = File(...),
    resume_name: str = Form(default=""),
    set_as_primary: bool = Form(default=False),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await ResumeService(db).upload_and_process(user_id, file, resume_name, set_as_primary)

@router.get("/", summary="List all resumes")
async def list_resumes(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    resumes = await ResumeService(db).list_resumes(user_id)
    return [{"id": r.id, "name": r.name, "file_name": r.file_name, "status": r.status.value, "is_primary": r.is_primary, "created_at": str(r.created_at)} for r in resumes]

@router.get("/{resume_id}", summary="Get resume metadata")
async def get_resume(resume_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    r = await ResumeService(db).get_resume(resume_id, user_id)
    return {"id": r.id, "name": r.name, "status": r.status.value, "is_primary": r.is_primary, "skill_count": len(r.parsed_skills.split(",")) if r.parsed_skills else 0}

@router.get("/{resume_id}/profile", summary="Get extracted AI profile from resume")
async def get_profile(resume_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await ResumeService(db).get_profile(resume_id, user_id)

@router.get("/{resume_id}/intelligence", summary="ATS score, quality analysis, and optional job tailoring")
async def get_intelligence(resume_id: str, job_description: str = "", user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await ResumeService(db).get_intelligence(resume_id, user_id, job_description or None)

@router.delete("/{resume_id}", status_code=204, summary="Delete a resume")
async def delete_resume(resume_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    await ResumeService(db).delete_resume(resume_id, user_id)

@router.put("/{resume_id}/primary", status_code=204, summary="Set as primary resume")
async def set_primary(resume_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    await ResumeService(db).set_primary(resume_id, user_id)
