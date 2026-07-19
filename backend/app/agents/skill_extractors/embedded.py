"""Embedded skill extractor — wraps the EXISTING embedded extraction logic
(app.resume.extractor.extract_skills) unchanged, behind the SkillExtractor
interface. Its output structure feeds domain_profile_data['embedded_engineering']
while the resume service continues to build the embedded CandidateProfile /
ai_summary exactly as before (zero behaviour change for embedded candidates)."""
from __future__ import annotations

from app.agents.skill_extractors.base import ExtractionResult, SkillExtractor
from app.resume.extractor import extract_skills


class EmbeddedSkillExtractor(SkillExtractor):
    domain_code = "embedded_engineering"
    profiling_level = "full"

    async def extract(self, resume_text: str, domain=None) -> ExtractionResult:
        s = extract_skills(resume_text)   # identical to the pre-Phase-4 path
        structured = {
            "programming": s.programming,
            "rtos_os": s.rtos_os,
            "protocols": s.protocols,
            "hardware": s.hardware,
            "automotive": s.automotive,
            "tools": s.tools,
            "concepts": s.concepts,
        }
        return ExtractionResult(self.domain_code, list(s.all_skills), structured, "full")
