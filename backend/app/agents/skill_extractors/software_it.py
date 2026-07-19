"""Software / IT skill extractor (non-embedded). Deterministic + offline.

Skills come from the Phase-3 software_it taxonomy; structured data captures the
candidate's primary stacks (languages, cloud, whether they show DevOps depth)."""
from __future__ import annotations

from app.agents.skill_extractors._seed_vocab import vocab_for
from app.agents.skill_extractors.base import ExtractionResult, SkillExtractor, match_vocab

_LANGS = {"python", "java", "javascript", "typescript", "go", "rust", "c#", "php", "ruby", "kotlin", "swift"}
_CLOUD = {"aws", "azure", "gcp"}


class SoftwareITSkillExtractor(SkillExtractor):
    domain_code = "software_it"
    profiling_level = "full"

    async def extract(self, resume_text: str, domain=None) -> ExtractionResult:
        skills = match_vocab(resume_text, vocab_for(self.domain_code))
        sset = set(skills)
        structured = {
            "languages": sorted(sset & _LANGS),
            "cloud_platforms": sorted(sset & _CLOUD),
            "has_devops": bool(sset & {"docker", "kubernetes", "ci/cd", "terraform", "jenkins", "devops"}),
            "has_data_layer": bool(sset & {"sql", "postgresql", "mysql", "mongodb", "redis", "nosql"}),
        }
        return ExtractionResult(self.domain_code, skills, structured, "full")
