"""EMBEDHUNT AI — Resume intelligence.

Offline, deterministic resume analysis:
  * ATS-readiness score (0-100) from section coverage, contact completeness,
    skill density, action verbs, quantified achievements, and length.
  * Quality signals + actionable suggestions.
  * Job tailoring — keyword coverage of a target job description with the exact
    missing skills to add.

Builds on the 300+ skill taxonomy (Module 3). No network, no LLM required.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from app.ai.skill_extractor import SkillExtractor
from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
_BULLET = re.compile(r"^\s*[-*•▪◦]\s+", re.M)
_NUMBER = re.compile(r"(\d+(?:\.\d+)?\s*%|\$\s*\d|\b\d+\s*(?:x|k|lpa|users|ms|kb|mb|gb|hours?|days?|weeks?|months?|years?|reduction|faster|improvement)\b|\b\d{2,}\b)", re.I)

_ACTION_VERBS = {
    "developed", "designed", "implemented", "built", "led", "optimized",
    "integrated", "debugged", "architected", "delivered", "reduced", "improved",
    "automated", "deployed", "migrated", "created", "engineered", "tested",
    "validated", "maintained", "refactored", "ported", "analyzed", "achieved",
    "spearheaded", "streamlined", "enhanced", "resolved", "programmed",
}
_CLICHES = {
    "team player", "hardworking", "hard working", "go-getter", "synergy",
    "think outside the box", "detail-oriented", "detail oriented",
    "self-motivated", "self motivated", "results-driven", "results driven",
    "go getter", "fast learner",
}
_SECTIONS = {
    "summary": re.compile(r"\b(summary|objective|profile)\b", re.I),
    "experience": re.compile(r"\b(experience|employment|work history)\b", re.I),
    "education": re.compile(r"\b(education|academics|qualification)\b", re.I),
    "skills": re.compile(r"\b(technical skills|skills|technologies|competenc)\b", re.I),
    "projects": re.compile(r"\b(projects?)\b", re.I),
}


@dataclass
class ResumeReport:
    ats_score: int
    has_email: bool
    has_phone: bool
    sections_found: list[str] = field(default_factory=list)
    skill_count: int = 0
    action_verb_count: int = 0
    quantified_bullets: int = 0
    bullet_count: int = 0
    word_count: int = 0
    cliches: list[str] = field(default_factory=list)
    top_skills: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ats_score": self.ats_score,
            "has_email": self.has_email,
            "has_phone": self.has_phone,
            "sections_found": self.sections_found,
            "skill_count": self.skill_count,
            "action_verb_count": self.action_verb_count,
            "quantified_bullets": self.quantified_bullets,
            "bullet_count": self.bullet_count,
            "word_count": self.word_count,
            "cliches": self.cliches,
            "top_skills": self.top_skills,
            "suggestions": self.suggestions,
        }


class ResumeIntelligence:
    def __init__(self, skill_extractor: SkillExtractor | None = None):
        self.skills = skill_extractor or SkillExtractor()

    def analyze(self, raw_text: str) -> ResumeReport:
        text = raw_text or ""
        lower = text.lower()
        words = re.findall(r"\S+", text)
        word_count = len(words)

        has_email = bool(_EMAIL.search(text))
        has_phone = bool(_PHONE.search(text))
        sections = [name for name, pat in _SECTIONS.items() if pat.search(text)]

        extracted = self.skills.extract(text)
        skill_count = len(extracted)
        top_skills = [s.name for s in extracted[:10]]

        action_verb_count = sum(len(re.findall(rf"\b{v}\b", lower)) for v in _ACTION_VERBS)
        bullets = _BULLET.findall(text)
        bullet_count = len(bullets)
        quantified = len(_NUMBER.findall(text))
        cliches = sorted({c for c in _CLICHES if c in lower})

        ats_score = self._ats_score(has_email, has_phone, sections, skill_count,
                                    action_verb_count, quantified, word_count)
        suggestions = self._suggestions(has_email, has_phone, sections, skill_count,
                                        action_verb_count, quantified, word_count, cliches)

        return ResumeReport(
            ats_score=ats_score, has_email=has_email, has_phone=has_phone,
            sections_found=sections, skill_count=skill_count,
            action_verb_count=action_verb_count, quantified_bullets=quantified,
            bullet_count=bullet_count, word_count=word_count, cliches=cliches,
            top_skills=top_skills, suggestions=suggestions,
        )

    async def analyze_ai(self, raw_text: str, *, db, user_id: str) -> ResumeReport:
        """Deterministic ``analyze`` enriched with LLM-parsed skills.

        External return type is unchanged (:class:`ResumeReport`). AI-discovered
        skills are unioned into ``top_skills``. Any failure, timeout, or the
        master toggle being off silently falls back to the deterministic report.
        """
        report = self.analyze(raw_text)
        if not settings.LLM_ENRICHMENT_ENABLED:
            logger.info("resume_intelligence_path", path="fallback", reason="disabled")
            return report
        try:
            from app.agents.resume_agent import ResumeAgent

            parsed = await asyncio.wait_for(
                ResumeAgent(db).parse(raw_text, user_id),
                timeout=settings.LLM_ENRICHMENT_TIMEOUT_SECONDS,
            )
            ai_skills = [s for s in (parsed.skills or []) if s]
            merged = list(dict.fromkeys([*report.top_skills, *ai_skills]))
            report.top_skills = merged[:20]
            report.skill_count = max(
                report.skill_count, len({s.lower() for s in report.top_skills})
            )
            logger.info(
                "resume_intelligence_path", path="ai_enriched", ai_skills=len(ai_skills)
            )
        except Exception as e:  # noqa: BLE001 — enrichment must never break the endpoint
            logger.warning("ai_enrichment_failed", module=__name__, error=str(e))
            return report
        return report

    def tailor_to_job(self, raw_text: str, job_description: str) -> dict:
        resume_skills = {s.name for s in self.skills.extract(raw_text)}
        job_skills = {s.name for s in self.skills.extract(job_description)}
        matched = sorted(resume_skills & job_skills)
        missing = sorted(job_skills - resume_skills)
        coverage = round(len(matched) / len(job_skills), 3) if job_skills else 0.0
        return {
            "coverage": coverage,
            "matched_skills": matched,
            "missing_skills": missing,
            "recommendation": self._tailor_recommendation(coverage, missing),
        }

    # ── scoring ──────────────────────────────────────────────────────────────
    @staticmethod
    def _ats_score(has_email, has_phone, sections, skill_count, action_verbs,
                   quantified, word_count) -> int:
        score = 0.0
        score += 8 if has_email else 0
        score += 7 if has_phone else 0
        score += 15 if "skills" in sections else 0
        score += 10 if "experience" in sections else 0
        score += 10 if "education" in sections else 0
        score += min(skill_count, 15) / 15 * 15
        score += min(action_verbs, 10) / 10 * 10
        score += min(quantified, 8) / 8 * 15
        if 250 <= word_count <= 900:
            score += 10
        elif word_count:
            score += max(0.0, 10 - abs(word_count - 575) / 90)
        return int(max(0, min(100, round(score))))

    @staticmethod
    def _suggestions(has_email, has_phone, sections, skill_count, action_verbs,
                     quantified, word_count, cliches) -> list[str]:
        tips: list[str] = []
        if not has_email:
            tips.append("Add a professional email address to the header.")
        if not has_phone:
            tips.append("Add a phone number for recruiters to reach you.")
        if "skills" not in sections:
            tips.append("Add a dedicated 'Technical Skills' section — ATS parsers rely on it.")
        if "experience" not in sections:
            tips.append("Add a clearly labelled 'Experience' section.")
        if "summary" not in sections:
            tips.append("Add a 2-3 line professional summary tailored to embedded roles.")
        if skill_count < 8:
            tips.append("List more concrete technical skills (languages, RTOS, protocols, tools).")
        if action_verbs < 5:
            tips.append("Start bullet points with strong action verbs (Developed, Optimized, Integrated).")
        if quantified < 3:
            tips.append("Quantify achievements with numbers (e.g., 'reduced boot time by 40%').")
        if word_count and word_count < 250:
            tips.append("Resume is thin — expand experience bullets with impact and scope.")
        if word_count > 1100:
            tips.append("Resume is long — trim to the most relevant 1-2 pages.")
        if cliches:
            tips.append(f"Remove clichés: {', '.join(cliches)}.")
        return tips

    @staticmethod
    def _tailor_recommendation(coverage: float, missing: list[str]) -> str:
        if coverage >= 0.8:
            return "Strong keyword match — resume is well tailored to this job."
        if coverage >= 0.5:
            gaps = ", ".join(missing[:5])
            return f"Decent match. Add these job keywords where truthful: {gaps}."
        gaps = ", ".join(missing[:8])
        return f"Low keyword coverage. Prioritise adding (if you have them): {gaps}."


_default: ResumeIntelligence | None = None


def get_resume_intelligence() -> ResumeIntelligence:
    global _default
    if _default is None:
        _default = ResumeIntelligence()
    return _default
