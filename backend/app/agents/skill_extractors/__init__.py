"""Domain-pluggable resume skill extractors (Phase 4)."""
from app.agents.skill_extractors.base import ExtractionResult, SkillExtractor
from app.agents.skill_extractors.registry import (
    extractors_for, get_extractor, has_plugin,
)
from app.agents.skill_extractors.resume_classifier import (
    ResumeDomainClassifier, ResumeDomainResult,
)

__all__ = [
    "ExtractionResult", "SkillExtractor", "get_extractor", "extractors_for",
    "has_plugin", "ResumeDomainClassifier", "ResumeDomainResult",
]
