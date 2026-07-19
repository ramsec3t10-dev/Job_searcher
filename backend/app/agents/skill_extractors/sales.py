"""Sales skill extractor. Deterministic + offline.

Beyond skills, captures the signals recruiters actually screen for: quota
attainment if the candidate stated it, CRM tools, and the industries they've
sold into."""
from __future__ import annotations

import re

from app.agents.skill_extractors._seed_vocab import vocab_for
from app.agents.skill_extractors.base import ExtractionResult, SkillExtractor, match_vocab

_CRM = {"salesforce", "hubspot", "crm", "outreach", "salesloft", "zoho crm", "pipedrive",
        "linkedin sales navigator"}
_INDUSTRIES = ("saas", "fintech", "healthcare", "manufacturing", "retail", "edtech",
               "cybersecurity", "logistics", "real estate", "insurance", "telecom",
               "automotive", "banking", "e-commerce", "ecommerce")

# "120% of quota", "achieved 150% quota", "quota attainment: 130%"
_QUOTA = re.compile(r"(\d{2,3})\s*%[^.\n]{0,25}\bquota\b|\bquota\b[^.\n]{0,25}?(\d{2,3})\s*%", re.I)


class SalesSkillExtractor(SkillExtractor):
    domain_code = "sales"
    profiling_level = "full"

    async def extract(self, resume_text: str, domain=None) -> ExtractionResult:
        skills = match_vocab(resume_text, vocab_for(self.domain_code))
        low = resume_text.lower()
        m = _QUOTA.search(resume_text)
        quota = None
        if m:
            quota = next((int(g) for g in m.groups() if g), None)
        structured = {
            "crm_tools": sorted(set(skills) & _CRM),
            "quota_attainment_pct": quota,
            "industries_sold_into": sorted({i for i in _INDUSTRIES if i in low}),
            "motion": [m for m in ("b2b sales", "enterprise sales", "saas", "consultative selling")
                       if m in set(skills)],
        }
        return ExtractionResult(self.domain_code, skills, structured, "full")
