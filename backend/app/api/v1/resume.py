"""EMBEDHUNT AI — Resume API"""
from fastapi import Body, APIRouter, HTTPException, Depends, File, Form, UploadFile, status
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


@router.post("/primary/skills", summary="Add curriculum-verified skills to the primary resume")
async def add_verified_skills(payload: dict = Body(...), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    skills = [str(s) for s in (payload.get("skills") or []) if str(s).strip()]
    if not skills:
        raise HTTPException(422, "Field 'skills' must be a non-empty list")
    return await ResumeService(db).add_verified_skills(user_id, skills)


@router.get("/primary/pdf", summary="Download the primary resume regenerated as a PDF from the live profile")
async def primary_resume_pdf(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """Always rendered from the CURRENT parsed profile — curriculum-verified
    skills added moments ago appear in this document immediately."""
    import json as _json

    from fastapi.responses import Response

    from app.repositories.user_repository import UserRepository
    from app.services.resume_renderer import render_resume_pdf

    svc = ResumeService(db)
    primary = await svc.repo.get_primary(user_id)
    if not primary or not primary.ai_summary:
        raise HTTPException(404, "No processed primary resume")
    user = await UserRepository(db).get_by_id(user_id)
    pdf = render_resume_pdf(
        _json.loads(primary.ai_summary),
        full_name=user.full_name if user else "Candidate",
        email=user.email if user else "",
        phone=getattr(user, "phone", None),
    )
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="resume.pdf"'})
