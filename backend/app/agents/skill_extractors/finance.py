"""Finance & accounting skill extractor. Deterministic + offline.

Captures certifications (CA / CFA / CPA / CMA / ACCA), the tools stack, and the
functional area (FP&A vs. audit vs. tax vs. treasury) — the axes finance roles
are actually hired along."""
from __future__ import annotations

import re

from app.agents.skill_extractors._seed_vocab import vocab_for
from app.agents.skill_extractors.base import ExtractionResult, SkillExtractor, match_vocab

# Certifications with word-boundary matching (CA/CFA/etc. are collision-prone).
_CERTS = {
    "ca": r"\bca\b|chartered accountant",
    "cfa": r"\bcfa\b|chartered financial analyst",
    "cpa": r"\bcpa\b|certified public accountant",
    "cma": r"\bcma\b|cost management accountant|certified management accountant",
    "acca": r"\bacca\b",
    "frm": r"\bfrm\b",
    "mba finance": r"mba\s*[-(]?\s*finance",
}
_TOOLS = {"sap", "tally", "quickbooks", "oracle financials", "netsuite", "xero", "erp"}
_FUNCTIONS = {
    "fp&a": r"fp&a|fpa|financial planning", "audit": r"\baudit", "tax": r"\btax",
    "treasury": r"treasury", "controllership": r"controller|controllership",
    "accounts payable": r"accounts payable|\bap\b", "accounts receivable": r"accounts receivable|\bar\b",
}


class FinanceSkillExtractor(SkillExtractor):
    domain_code = "finance"
    profiling_level = "full"

    async def extract(self, resume_text: str, domain=None) -> ExtractionResult:
        skills = match_vocab(resume_text, vocab_for(self.domain_code))
        low = resume_text.lower()
        certs = sorted(name for name, pat in _CERTS.items() if re.search(pat, low))
        functions = sorted(name for name, pat in _FUNCTIONS.items() if re.search(pat, low))
        structured = {
            "certifications": certs,
            "tools": sorted(set(skills) & _TOOLS),
            "functional_areas": functions,
        }
        return ExtractionResult(self.domain_code, skills, structured, "full")
