"""Base interface for domain-pluggable resume skill extraction (Phase 4).

Every domain provides a ``SkillExtractor`` that turns raw resume text into a
normalized :class:`ExtractionResult`: a flat skill list (feeds matching's
``all_skills``) plus a ``structured`` dict of domain-specific fields (feeds
candidate_profiles.domain_profile_data[domain_code]).

``profiling_level`` is "full" for domains with a dedicated plugin and researched
skill taxonomy, "basic" for the generic LLM/heuristic fallback — so the product
can honestly show the user whether they got deep or shallow profiling.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    domain_code: str
    skills: list[str] = field(default_factory=list)
    structured: dict = field(default_factory=dict)
    profiling_level: str = "full"          # "full" | "basic"

    def to_dict(self) -> dict:
        return {
            "domain_code": self.domain_code,
            "skills": self.skills,
            "structured": self.structured,
            "profiling_level": self.profiling_level,
        }


class SkillExtractor(ABC):
    #: The domain this extractor serves.
    domain_code: str = ""
    profiling_level: str = "full"

    @abstractmethod
    async def extract(self, resume_text: str, domain=None) -> ExtractionResult:
        """Extract skills + structured data from ``resume_text``. ``domain`` is an
        optional ``JobDomain`` (unused by the deterministic extractors)."""
        raise NotImplementedError


# ── Shared helpers for the deterministic keyword-based extractors ────────────
def match_vocab(text: str, canonical_to_aliases: dict[str, list[str]]) -> list[str]:
    """Return canonical skills whose name or any alias appears in ``text``
    (word-boundary, case-insensitive). Short (<=2 char) tokens require exact
    word boundaries to avoid substring collisions."""
    low = f" {text.lower()} "
    found: list[str] = []
    for canonical, aliases in canonical_to_aliases.items():
        for term in (canonical, *aliases):
            t = term.lower()
            esc = re.escape(t)
            pat = rf"\b{esc}\b" if (t[:1].isalnum() and t[-1:].isalnum()) else rf"(?<![a-z0-9]){esc}(?![a-z0-9])"
            if re.search(pat, low):
                found.append(canonical)
                break
    return found
