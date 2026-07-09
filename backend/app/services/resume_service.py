"""EMBEDHUNT AI — Resume Service (full pipeline orchestrator)"""
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.resume_repository import ResumeRepository
from app.models.resume import Resume, ResumeStatus
from app.resume.parser import parse_resume
from app.resume.extractor import extract_skills, extract_experience
from app.resume.normalizer import build_profile
from app.resume.validator import validate_resume_file, validate_parsed_text
from app.config.logging import get_logger
from sqlalchemy import update

logger = get_logger(__name__)

class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ResumeRepository(db)

    async def upload_and_process(self, user_id: str, file: UploadFile, name: str, set_primary: bool = False) -> dict:
        content = await validate_resume_file(file)
        filename = file.filename or "resume.pdf"
        if set_primary:
            await self.repo.clear_primary(user_id)
        resume = await self.repo.create(
            user_id=user_id, name=name.strip() or filename,
            file_url=f"local://{uuid.uuid4()}/{filename}",
            file_name=filename, file_size_bytes=len(content),
            file_type=filename.rsplit(".", 1)[-1].lower(),
            is_primary=set_primary, status=ResumeStatus.UPLOADED
        )
        await self.repo.set_status(resume.id, ResumeStatus.PARSING)
        try:
            doc = parse_resume(filename, content)
        except Exception as e:
            await self.repo.set_status(resume.id, ResumeStatus.PARSE_FAILED)
            raise HTTPException(500, f"Parse failed: {e}")
        try:
            validate_parsed_text(doc.raw_text)
        except HTTPException:
            await self.repo.set_status(resume.id, ResumeStatus.PARSE_FAILED)
            raise
        skills = extract_skills(doc.raw_text)
        exp = extract_experience(doc.raw_text)
        profile = build_profile(doc.raw_text, skills, exp)
        await self.repo.save_parsed(
            resume.id,
            raw_text=doc.raw_text[:50000],
            parsed_skills=skills.to_csv(),
            parsed_experience=exp.to_json(),
            ai_summary=profile.to_json(),
        )
        logger.info("resume_processed", resume_id=resume.id, skills=skills.count(), yoe=exp.total_years)
        return {
            "resume_id": resume.id, "status": "parsed",
            "skills_count": skills.count(),
            "years_experience": exp.total_years,
            "is_embedded_engineer": profile.is_embedded_engineer,
            "embedded_domain_score": profile.embedded_domain_score,
            "top_skills": profile.all_skills[:10],
            "warnings": doc.warnings,
            "message": f"Parsed successfully. {skills.count()} skills found, ~{exp.total_years:.1f} YoE, domain score {profile.embedded_domain_score}/100."
        }

    async def list_resumes(self, user_id: str) -> list[Resume]:
        return await self.repo.get_by_user(user_id)

    async def get_resume(self, resume_id: str, user_id: str) -> Resume:
        r = await self.repo.get_for_user(resume_id, user_id)
        if not r: raise HTTPException(404, "Resume not found")
        return r

    async def get_profile(self, resume_id: str, user_id: str) -> dict:
        import json
        r = await self.get_resume(resume_id, user_id)
        if not r.ai_summary: raise HTTPException(409, f"Not yet processed. Status: {r.status.value}")
        return json.loads(r.ai_summary)

    async def delete_resume(self, resume_id: str, user_id: str):
        r = await self.get_resume(resume_id, user_id)
        await self.repo.delete(r)

    async def get_intelligence(self, resume_id: str, user_id: str, job_description: str | None = None) -> dict:
        from app.ai.resume_intelligence import get_resume_intelligence
        r = await self.get_resume(resume_id, user_id)
        if not r.raw_text:
            raise HTTPException(409, f"Not yet processed. Status: {r.status.value}")
        analyzer = get_resume_intelligence()
        report = (await analyzer.analyze_ai(r.raw_text, db=self.db, user_id=user_id)).to_dict()
        if job_description:
            report["tailoring"] = analyzer.tailor_to_job(r.raw_text, job_description)
        return report

    async def set_primary(self, resume_id: str, user_id: str):
        r = await self.get_resume(resume_id, user_id)
        await self.repo.clear_primary(user_id)
        from sqlalchemy import update as sq_update
        await self.db.execute(sq_update(Resume).where(Resume.id == r.id).values(is_primary=True))
