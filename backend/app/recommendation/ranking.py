"""EMBEDHUNT AI — Ranking Engine"""
from dataclasses import dataclass, field
from enum import Enum
from app.domains.catalog import DEFAULT_DOMAIN_CODE, code_for_domain_id
from app.recommendation.matcher import (
    DomainScoringConfig, MatchScore, compute_match, generic_config,
)
from app.recommendation.explain import GapAnalysis, analyze_gaps
from app.resume.normalizer import CandidateProfile

class MatchTier(str, Enum):
    AUTO_APPLY="auto_apply"; STRONG="strong"; GOOD="good"; PARTIAL="partial"

@dataclass
class RankedJob:
    rank: int; job_id: str; title: str; company: str; company_tier: str
    location: str; source_portal: str; source_url: str; apply_url: str|None
    salary_min_lpa: float|None; salary_max_lpa: float|None; meets_salary: bool
    match_score: int; match_tier: MatchTier; is_auto_apply: bool
    match: MatchScore; gap: GapAnalysis
    domain_id: str | None = None

@dataclass
class RankingResult:
    candidate: str; total_scanned: int; total_qualified: int
    auto_apply_count: int; strong_count: int
    salary_filter: str; summary: str
    jobs: list[RankedJob] = field(default_factory=list)

def _meets_salary(sal_min, sal_max, required) -> bool:
    if sal_max is not None and sal_max >= required: return True
    if sal_min is not None and sal_min >= required: return True
    return sal_min is None and sal_max is None

def _tier(score: int, meets: bool) -> MatchTier:
    if score >= 85 and meets: return MatchTier.AUTO_APPLY
    if score >= 70: return MatchTier.STRONG
    if score >= 55: return MatchTier.GOOD
    return MatchTier.PARTIAL

def _config_for_job(job: dict, scoring: dict[str, DomainScoringConfig] | None):
    """Resolve the scoring config for a job by its domain.

    * Untagged jobs and embedded jobs use the embedded path (in-code default when
      no registry; the DB-weighted embedded config when a registry is supplied —
      proven identical by the Phase-3 regression test).
    * Seeded non-embedded domains use their own DB-driven weights.
    * Tagged-but-unseeded domains use a generic skill-overlap config (no
      fabricated per-domain weighting).
    """
    code = code_for_domain_id(job.get("domain_id")) or DEFAULT_DOMAIN_CODE
    if scoring and code in scoring:
        return scoring[code]
    if code == DEFAULT_DOMAIN_CODE:
        return None            # embedded default — identical to pre-Phase-3
    return generic_config()


def rank_jobs(profile: CandidateProfile, jobs: list[dict], min_score: int=40,
              salary_min: float=15.0, *,
              scoring: dict[str, DomainScoringConfig] | None = None,
              target_domains: set | None = None) -> RankingResult:
    ranked = []
    for job in jobs:
        config = _config_for_job(job, scoring)
        match = compute_match(profile, job.get("title",""), job.get("description"), job.get("required_skills"), job.get("experience_min"), job.get("experience_max"), config=config, target_domains=target_domains)
        if match.total_score < min_score: continue
        sal_min_j, sal_max_j = job.get("salary_min_lpa"), job.get("salary_max_lpa")
        meets = _meets_salary(sal_min_j, sal_max_j, salary_min)
        tier = _tier(match.total_score, meets)
        gap = analyze_gaps(match, job.get("title",""))
        ranked.append(RankedJob(0, job.get("id",""), job.get("title",""), job.get("company",""), job.get("company_tier",""), job.get("location",""), job.get("source_portal",""), job.get("source_url",""), job.get("apply_url"), sal_min_j, sal_max_j, meets, match.total_score, tier, match.total_score>=85 and meets, match, gap, job.get("domain_id")))
    ranked.sort(key=lambda j: (not j.is_auto_apply, not j.meets_salary, -j.match_score))
    for i,j in enumerate(ranked,1): j.rank = i
    auto = sum(1 for j in ranked if j.is_auto_apply)
    strong = sum(1 for j in ranked if j.match_tier == MatchTier.STRONG)
    return RankingResult(profile.name_hint or "Candidate", len(jobs), len(ranked), auto, strong, f"≥{salary_min} LPA", f"Scanned {len(jobs)} → {len(ranked)} qualified. {auto} auto-apply.", ranked)
