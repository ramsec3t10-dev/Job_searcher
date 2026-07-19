"""Generic skill extractor — the honest fallback for domains without a dedicated
plugin yet. Pulls skills from the resume's own skills/tools sections
heuristically (offline), optionally enriched by an LLM when a router is
available. Always tagged ``profiling_level="basic"`` so the product can tell the
user they got basic (not full) profiling for their field."""
from __future__ import annotations

import re

from app.config.settings import settings
from app.agents.skill_extractors.base import ExtractionResult, SkillExtractor
from app.llm.model_selector import TaskType

# Header optionally followed by inline content on the same line:
# "Skills: a, b, c"  OR  a bare "Skills:" header line.
_SECTION_HDR = re.compile(
    r"^\s*(?:technical\s+skills|core\s+competencies|skills|tools|technologies|"
    r"key\s+skills|areas\s+of\s+expertise|proficiencies)\s*[:\-]?\s*(.*)$", re.I)
_SPLIT = re.compile(r"[,•|/;\t]|\s{2,}")


class GenericSkillExtractor(SkillExtractor):
    domain_code = "generic"
    profiling_level = "basic"

    def __init__(self, router=None, domain_code: str = "generic") -> None:
        self.router = router
        self.domain_code = domain_code

    def _heuristic(self, resume_text: str) -> list[str]:
        lines = resume_text.split("\n")
        out: list[str] = []
        capture = 0

        def _collect(fragment: str) -> None:
            for tok in _SPLIT.split(fragment):
                t = tok.strip().lower().strip(".")
                if 2 <= len(t) <= 40 and not t.isdigit() and any(c.isalpha() for c in t):
                    out.append(t)

        for line in lines:
            m = _SECTION_HDR.match(line)
            if m:
                capture = 6
                if m.group(1).strip():          # inline "Skills: a, b, c"
                    _collect(m.group(1))
                continue
            if capture > 0:
                capture -= 1
                _collect(line)
        # de-dup, keep order, cap
        seen: set[str] = set()
        skills = [s for s in out if not (s in seen or seen.add(s))]
        return skills[:40]

    async def extract(self, resume_text: str, domain=None) -> ExtractionResult:
        skills = self._heuristic(resume_text)
        if self.router is not None and settings.LLM_ENRICHMENT_ENABLED:
            try:
                skills = await self._llm_skills(resume_text) or skills
            except Exception:  # noqa: BLE001 — enrichment must never break parsing
                pass
        return ExtractionResult(self.domain_code, skills, {"note": "basic profiling"}, "basic")

    async def _llm_skills(self, resume_text: str) -> list[str]:
        system = ('Extract the candidate\'s professional skills from the resume. '
                  'Respond ONLY with a JSON array of lowercase skill strings.')
        resp = await self.router.route(
            TaskType.DOMAIN_CLASSIFICATION,
            [{"role": "user", "content": resume_text[:4000]}],
            system=system)
        import json
        text = (resp.content or "").strip()
        a, b = text.find("["), text.rfind("]")
        if a != -1 and b > a:
            try:
                data = json.loads(text[a:b + 1])
                return [str(x).strip().lower() for x in data if str(x).strip()][:40]
            except json.JSONDecodeError:
                return []
        return []
