"""Resume → domain classification (Phase 4).

Classifies resume text to a profiling domain, choosing among the domains that
actually have an extractor plugin (embedded_engineering, software_it, sales,
finance) plus the other top-level domains (which fall back to generic
profiling). Scoring is word-boundary based over each domain's role titles AND
seeded skills — resumes list skills more than role titles, and short tokens
("can", "go") must not collide inside words. The optional LLM tier (Haiku, via
the same AIRouter → domain_classification path) resolves ambiguous resumes and
never blocks parsing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config.settings import settings
from app.domains.catalog import domain_id, flatten, top_level_domains
from app.domains.skill_seed import DOMAIN_SKILL_SEED
from app.job_sources.domain_classifier import DomainClassifier
from app.resume.extractor import ALL_SKILLS as _EMBEDDED_SKILLS

# Domains that have a dedicated extractor plugin (mixed levels).
_PLUGGED = {"embedded_engineering", "software_it", "sales", "finance"}
_MIN_TERM_LEN = 3  # skip 1-2 char tokens ("c","go") — too collision-prone as keywords


def _wb(term: str, text: str) -> bool:
    esc = re.escape(term)
    pat = rf"\b{esc}\b" if (term[:1].isalnum() and term[-1:].isalnum()) else rf"(?<![a-z0-9]){esc}(?![a-z0-9])"
    return re.search(pat, text) is not None


@dataclass
class _Target:
    code: str
    name: str
    roles: frozenset      # role/title phrases
    skills: frozenset     # skill keywords


def _build_targets() -> list[_Target]:
    """Targets = plugged domains (with embedded split out of software_it) + other
    top-level domains, each with role phrases + seeded skills as keywords."""
    tops = {d.code: d for d in top_level_domains()}
    emb = next(d for d in flatten() if d.code == "embedded_engineering")
    emb_roles = {k for k in emb.keywords if len(k) >= _MIN_TERM_LEN}
    emb_skills = {s for s in _EMBEDDED_SKILLS if len(s) >= _MIN_TERM_LEN}

    def seeded_skills(code: str) -> set[str]:
        out: set[str] = set()
        for _cc, _cn, _w, skills in DOMAIN_SKILL_SEED.get(code, []):
            for name, aliases in skills:
                for t in (name, *aliases):
                    if len(t) >= _MIN_TERM_LEN:
                        out.add(t.lower())
        return out

    targets = [_Target("embedded_engineering", "Embedded Systems",
                       frozenset(emb_roles), frozenset(emb_skills))]
    for code, d in tops.items():
        roles = {k for k in d.keywords if len(k) >= _MIN_TERM_LEN}
        if code == "software_it":
            roles = roles - set(emb.keywords)        # keep embedded distinct
        targets.append(_Target(code, d.name, frozenset(roles), frozenset(seeded_skills(code))))
    return targets


@dataclass
class ResumeDomainResult:
    primary: str
    confidence: float
    secondary: list[str] = field(default_factory=list)
    method: str = "rule"

    @property
    def primary_domain_id(self) -> str:
        return domain_id(self.primary)

    @property
    def secondary_domain_ids(self) -> list[str]:
        return [domain_id(c) for c in self.secondary]


class ResumeDomainClassifier:
    _SECONDARY_MIN = 0.55
    _SECONDARY_MARGIN = 0.35

    def __init__(self, router=None, *, min_rule_confidence: float = 0.55) -> None:
        self.router = router
        self.min_rule_confidence = min_rule_confidence
        self._targets = _build_targets()

    def _score(self, tgt: _Target, role_low: str, text_low: str) -> float:
        score = 0.0
        for kw in tgt.roles:
            if role_low and _wb(kw, role_low):
                score = max(score, 0.95)              # role title is the strongest signal
            elif _wb(kw, text_low):
                score = max(score, 0.6)
        hits = sum(1 for s in tgt.skills if _wb(s, text_low))
        score += min(0.4, hits * 0.08)                # skills reinforce, capped
        return min(score, 1.0)

    def score_all(self, resume_text: str, role_hint: str = "") -> dict[str, float]:
        text_low = f" {(resume_text or '').lower()} "
        role_low = f" {(role_hint or '').lower()} "
        scores: dict[str, float] = {}
        for tgt in self._targets:
            s = self._score(tgt, role_low, text_low)
            if s > 0:
                scores[tgt.code] = round(s, 2)
        return scores

    def classify_rule(self, resume_text: str, role_hint: str = "") -> ResumeDomainResult | None:
        scores = self.score_all(resume_text, role_hint)
        if not scores:
            return None
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        primary, top = ranked[0]
        secondary = [
            code for code, s in ranked[1:]
            if s >= self._SECONDARY_MIN and (top - s) <= self._SECONDARY_MARGIN
        ][:2]
        return ResumeDomainResult(primary, round(top, 2), secondary, "rule")

    async def classify(self, resume_text: str, role_hint: str = "", *,
                       user_id: str | None = None, db=None) -> ResumeDomainResult:
        rule = self.classify_rule(resume_text, role_hint)
        if rule and rule.confidence >= self.min_rule_confidence:
            return rule
        if self.router is not None and settings.LLM_ENRICHMENT_ENABLED:
            clf = DomainClassifier(router=self.router)
            llm = await clf._classify_llm(role_hint or "Candidate", resume_text,
                                          user_id=user_id, db=db)
            if llm is not None:
                return ResumeDomainResult(llm.code, llm.confidence,
                                          rule.secondary if rule else [], "llm")
        if rule is not None:
            return ResumeDomainResult(rule.primary, rule.confidence, rule.secondary, "rule_low")
        return ResumeDomainResult("other", 0.0, [], "fallback")
