"""FROZEN Phase-3 regression baseline — verbatim copy of the pre-Phase-3 matcher. Do not edit."""
from dataclasses import dataclass, field
from app.resume.normalizer import CandidateProfile
from app.resume.extractor import PROGRAMMING, RTOS_OS, PROTOCOLS, HARDWARE, AUTOMOTIVE, TOOLS, CONCEPTS

WEIGHTS = {"programming":20,"rtos_os":20,"protocols":20,"hardware":15,"automotive":15,"tools":5,"concepts":5}
CATEGORY_SETS = {"programming":PROGRAMMING,"rtos_os":RTOS_OS,"protocols":PROTOCOLS,"hardware":HARDWARE,"automotive":AUTOMOTIVE,"tools":TOOLS,"concepts":CONCEPTS}
PROFILE_ATTRS = {"programming":"programming_languages","rtos_os":"rtos_and_os","protocols":"protocols","hardware":"hardware_platforms","automotive":"automotive_safety","tools":"tools_and_debug","concepts":"software_concepts"}

@dataclass
class CategoryScore:
    category: str; weight: int; candidate_skills: list[str]; job_skills: list[str]
    matched_skills: list[str]; raw_score: float; weighted_score: float

@dataclass
class MatchScore:
    total_score: int; base_score: float; experience_bonus: int; domain_bonus: int
    category_scores: list[CategoryScore] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    job_required_skills: list[str] = field(default_factory=list)
    explanation: str = ""; recommendation: str = ""

def _split(s: str|None) -> list[str]:
    if not s: return []
    return [x.strip().lower() for x in s.replace(";",",").replace("|",",").split(",") if x.strip()]

def compute_match(profile: CandidateProfile, title: str, description: str|None, required_skills: str|None, exp_min: int|None=None, exp_max: int|None=None) -> MatchScore:
    job_text = " ".join(filter(None,[title,description,required_skills])).lower()
    job_flat = set(_split(required_skills))
    cat_scores = []; base = 0.0; all_matched: set[str] = set(); all_job: set[str] = set()

    for cat, weight in WEIGHTS.items():
        skill_set = CATEGORY_SETS[cat]
        job_cat = {s for s in skill_set if s in job_text} | (job_flat & skill_set)
        cand_cat = set(getattr(profile, PROFILE_ATTRS[cat], []))
        matched = sorted(cand_cat & job_cat)
        all_matched.update(matched); all_job.update(job_cat)
        raw = min(1.0, len(matched)/len(job_cat)) if job_cat else 0.0
        weighted = raw * weight; base += weighted
        cat_scores.append(CategoryScore(cat, weight, sorted(cand_cat), sorted(job_cat), matched, round(raw,3), round(weighted,2)))

    exp_bonus = 0
    if exp_min is not None: exp_bonus = 5 if profile.total_years_experience >= exp_min else (2 if profile.total_years_experience >= exp_min*0.75 else 0)
    else: exp_bonus = 3

    embedded_kw = {"embedded","firmware","automotive","autosar","adas","ecu","rtos","firmware"}
    domain_bonus = 5 if any(k in job_text for k in embedded_kw) and profile.is_embedded_engineer else 0

    total = max(0, min(99, int(base + exp_bonus + domain_bonus)))
    missing = sorted(all_job - all_matched)
    explanation = _explain(cat_scores, all_matched, missing, total)
    recommendation = "strong_match" if total>=85 else "good_match" if total>=70 else "partial_match" if total>=50 else "low_match"

    return MatchScore(total, round(base,2), exp_bonus, domain_bonus, cat_scores, sorted(all_matched), missing, sorted(all_job), explanation, recommendation)

def _explain(cats, matched, missing, total):
    parts = []
    top = sorted([c for c in cats if c.matched_skills], key=lambda c: c.weighted_score, reverse=True)[:3]
    if top: parts.append("Matches: " + "; ".join(f"{c.category.replace('_',' ')}: {','.join(c.matched_skills[:3])}" for c in top) + ".")
    if missing: parts.append(f"Gaps: {', '.join(missing[:5])}{'...' if len(missing)>5 else ''}.")
    parts.append({True:"Excellent fit."}.get(total>=85,"Good fit." if total>=70 else "Partial fit." if total>=50 else "Low overlap."))
    return " ".join(parts)
