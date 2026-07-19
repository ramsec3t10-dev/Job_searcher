"""EMBEDHUNT AI — Resume Service (full pipeline orchestrator)"""
import json
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
from app.config.settings import settings
from sqlalchemy import select, update

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

        # ── Phase 4: domain classification + pluggable extraction ──────────
        # For embedded candidates the profile / ai_summary is left byte-identical
        # to the pre-Phase-4 pipeline; other domains additionally get their
        # skills merged into all_skills so matching works, plus structured
        # per-domain data written to candidate_profiles.domain_profile_data.
        domain_meta = await self._profile_domains(user_id, doc.raw_text, exp, profile)

        await self.repo.save_parsed(
            resume.id,
            raw_text=doc.raw_text[:50000],
            parsed_skills=skills.to_csv(),
            parsed_experience=exp.to_json(),
            ai_summary=profile.to_json(),
        )
        logger.info("resume_processed", resume_id=resume.id, skills=len(profile.all_skills),
                    yoe=exp.total_years, primary_domain=domain_meta.get("primary"))
        return {
            "resume_id": resume.id, "status": "parsed",
            "skills_count": len(profile.all_skills),
            "years_experience": exp.total_years,
            "is_embedded_engineer": profile.is_embedded_engineer,
            "embedded_domain_score": profile.embedded_domain_score,
            "primary_domain": domain_meta.get("primary"),
            "secondary_domains": domain_meta.get("secondary", []),
            "profiling_level": domain_meta.get("profiling_level", "full"),
            "top_skills": profile.all_skills[:10],
            "warnings": doc.warnings,
            "message": f"Parsed successfully. {len(profile.all_skills)} skills found, "
                       f"~{exp.total_years:.1f} YoE, domain: {domain_meta.get('primary')}."
        }

    async def _profile_domains(self, user_id: str, raw_text: str, exp, profile) -> dict:
        """Classify the resume's domain(s), run the matching extractor plugin(s),
        merge non-embedded skills into ``profile.all_skills`` and persist
        primary/secondary domains + structured data to candidate_profiles.
        Never raises — profiling failure must not fail resume upload."""
        try:
            from app.agents.skill_extractors import ResumeDomainClassifier, extractors_for
            from app.models.profile import CandidateProfile

            router = None
            if settings.LLM_ENRICHMENT_ENABLED:
                try:
                    from app.llm.router import AIRouter
                    router = AIRouter()
                except Exception:  # noqa: BLE001
                    router = None

            clf = ResumeDomainClassifier(router=router)
            det = await clf.classify(raw_text, role_hint=exp.current_role or "",
                                     user_id=user_id, db=self.db)

            extractors = extractors_for(det.primary, det.secondary, router=router)
            embedded_primary = det.primary == "embedded_engineering"
            domain_data: dict = {}
            level = "full"
            for ext in extractors:
                res = await ext.extract(raw_text)
                domain_data[ext.domain_code] = res.to_dict()
                if res.profiling_level == "basic":
                    level = "basic"
                # Merge extracted skills into all_skills so non-embedded matching
                # has signal. Embedded-primary candidates are left byte-identical
                # to the pre-Phase-4 pipeline (no merge at all).
                if not embedded_primary and ext.domain_code != "embedded_engineering":
                    have = {s.lower() for s in profile.all_skills}
                    for s in res.skills:
                        if s.lower() not in have:
                            profile.all_skills.append(s)
                            have.add(s.lower())
            if not embedded_primary:
                profile.skill_count = len(profile.all_skills)

            # Upsert the candidate_profiles row (Phase 1 columns).
            row = (await self.db.execute(select(CandidateProfile).where(
                CandidateProfile.user_id == user_id))).scalar_one_or_none()
            if row is None:
                row = CandidateProfile(user_id=user_id)
                self.db.add(row)
            row.primary_domain_id = det.primary_domain_id
            row.secondary_domain_ids = det.secondary_domain_ids
            merged = dict(row.domain_profile_data or {})
            merged.update(domain_data)
            row.domain_profile_data = merged
            await self.db.flush()
            return {"primary": det.primary, "secondary": det.secondary,
                    "profiling_level": level}
        except Exception as exc:  # noqa: BLE001
            logger.warning("domain_profiling_failed", error=str(exc))
            return {"primary": None, "secondary": [], "profiling_level": "full"}

    async def add_verified_skills(self, user_id: str, skills: list[str]) -> dict:
        """Adds curriculum-verified skills to the PRIMARY resume's parsed
        profile — the exact profile the matching engine and auto-apply use —
        so every future application goes out with the updated resume."""
        primary = await self.repo.get_primary(user_id)
        if not primary or not primary.ai_summary:
            raise HTTPException(404, "No processed primary resume to update")
        profile = json.loads(primary.ai_summary)
        existing = {s.lower() for s in profile.get("all_skills", [])}
        added = []
        for skill in skills:
            sk = (skill or "").strip()
            if sk and sk.lower() not in existing:
                profile.setdefault("all_skills", []).append(sk)
                added.append(sk)
        if added:
            primary.ai_summary = json.dumps(profile)
            await self.db.flush()
        return {"added": added,
                "total_skills": len(profile.get("all_skills", [])),
                "message": ("Resume updated — auto-apply now uses it" if added
                            else "Those skills were already on your resume")}

    async def list_resumes(self, user_id: str) -> list[Resume]:
        return await self.repo.get_by_user(user_id)

    async def get_resume(self, resume_id: str, user_id: str) -> Resume:
        r = await self.repo.get_for_user(resume_id, user_id)
        if not r: raise HTTPException(404, "Resume not found")
        return r

    async def get_profile(self, resume_id: str, user_id: str) -> dict:
        r = await self.get_resume(resume_id, user_id)
        if not r.ai_summary: raise HTTPException(409, f"Not yet processed. Status: {r.status.value}")
        data = json.loads(r.ai_summary)
        # Additive Phase-4 domain block (never breaks existing consumers).
        try:
            from app.services.profile_service import ProfileService
            data["domain"] = await ProfileService(self.db).domain_block(user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("profile_domain_block_failed", error=str(exc))
        return data

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
