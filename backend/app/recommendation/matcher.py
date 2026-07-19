"""EMBEDHUNT AI — Matching Engine (weighted category scoring).

Domain-generalised in Phase 3: scoring is driven by a ``DomainScoringConfig``
(category weights + skill vocabularies) instead of a hardcoded embedded table.
The **default config reproduces the previous embedded scoring exactly** — the
Phase-3 regression test (tests/unit/test_scoring_regression.py) asserts the
config-driven path yields identical scores for embedded jobs, including when the
config's weights are loaded from the Phase-1 SkillCategory rows.
"""
from dataclasses import dataclass, field

from app.resume.normalizer import CandidateProfile
from app.resume.extractor import PROGRAMMING, RTOS_OS, PROTOCOLS, HARDWARE, AUTOMOTIVE, TOOLS, CONCEPTS

# ── Embedded reference tables (also the default config's source) ─────────────
WEIGHTS = {"programming":20,"rtos_os":20,"protocols":20,"hardware":15,"automotive":15,"tools":5,"concepts":5}
CATEGORY_SETS = {"programming":PROGRAMMING,"rtos_os":RTOS_OS,"protocols":PROTOCOLS,"hardware":HARDWARE,"automotive":AUTOMOTIVE,"tools":TOOLS,"concepts":CONCEPTS}
PROFILE_ATTRS = {"programming":"programming_languages","rtos_os":"rtos_and_os","protocols":"protocols","hardware":"hardware_platforms","automotive":"automotive_safety","tools":"tools_and_debug","concepts":"software_concepts"}

_EMBEDDED_KW = {"embedded","firmware","automotive","autosar","adas","ecu","rtos"}


@dataclass(frozen=True)
class CategoryConfig:
    """One weighted skill category. ``vocab`` is the category's skill vocabulary;
    ``profile_attr`` names a pre-bucketed CandidateProfile attribute (embedded
    path) — when None, candidate skills are drawn from ``all_skills``. When
    ``universal`` is set the category ignores ``vocab`` and scores the
    candidate's whole skill set against the job's stated required skills — an
    honest, domain-agnostic overlap used for domains without seeded weights yet."""
    code: str
    weight: int
    vocab: frozenset               # canonical skill names
    profile_attr: str | None = None
    universal: bool = False
    # (alias, canonical) pairs so synonyms collapse to one skill instead of
    # being double-counted (e.g. "pipeline" → "pipeline management"). Empty for
    # embedded, keeping the embedded path byte-identical.
    alias_pairs: tuple = ()


def generic_config() -> DomainScoringConfig:
    """Domain-agnostic fallback: skill overlap vs the job's required skills. Used
    for domains whose real SkillCategory weights are not seeded yet (no fabricated
    per-domain weighting — just direct overlap)."""
    return DomainScoringConfig(
        "generic", (CategoryConfig("skills", 100, frozenset(), None, universal=True),))


@dataclass(frozen=True)
class DomainScoringConfig:
    domain_code: str
    categories: tuple  # tuple[CategoryConfig, ...]
    embedded_bonus: bool = False   # True → legacy embedded keyword/domain bonus


def embedded_default_config() -> DomainScoringConfig:
    """The embedded scoring profile, byte-compatible with the pre-Phase-3 code.
    Category order follows WEIGHTS insertion order so explanations are identical."""
    cats = tuple(
        CategoryConfig(code, WEIGHTS[code], frozenset(CATEGORY_SETS[code]), PROFILE_ATTRS[code])
        for code in WEIGHTS
    )
    return DomainScoringConfig("embedded_engineering", cats, embedded_bonus=True)


@dataclass
class CategoryScore:
    category: str; weight: int; candidate_skills: list; job_skills: list
    matched_skills: list; raw_score: float; weighted_score: float

@dataclass
class MatchScore:
    total_score: int; base_score: float; experience_bonus: int; domain_bonus: int
    category_scores: list = field(default_factory=list)
    matched_skills: list = field(default_factory=list)
    missing_skills: list = field(default_factory=list)
    job_required_skills: list = field(default_factory=list)
    explanation: str = ""; recommendation: str = ""

def _split(s):
    if not s: return []
    return [x.strip().lower() for x in s.replace(";",",").replace("|",",").split(",") if x.strip()]

def compute_match(profile: CandidateProfile, title, description, required_skills,
                  exp_min=None, exp_max=None, *,
                  config: DomainScoringConfig | None = None,
                  target_domains: set | None = None) -> MatchScore:
    config = config or embedded_default_config()
    job_text = " ".join(filter(None,[title,description,required_skills])).lower()
    job_flat = set(_split(required_skills))
    cat_scores = []; base = 0.0; all_matched: set = set(); all_job: set = set()

    for cc in config.categories:
        if cc.universal:
            # Overlap the whole candidate skill set with the job's required skills.
            job_cat = set(job_flat)
            cand_cat = set(getattr(profile, "all_skills", []))
        elif not cc.alias_pairs:
            # Embedded / alias-free path — unchanged (regression-critical).
            skill_set = cc.vocab
            job_cat = {s for s in skill_set if s in job_text} | (job_flat & skill_set)
            if cc.profile_attr is not None:
                cand_cat = set(getattr(profile, cc.profile_attr, []))
            else:
                cand_cat = {s for s in getattr(profile, "all_skills", []) if s in skill_set}
        else:
            # Generic domains with aliases: normalise aliases to canonical skills
            # so synonyms match and never appear as phantom gaps. Single-word
            # skills come only from the structured required_skills list (clean),
            # avoiding substring collisions like "go" inside "django" or "sql"
            # inside "postgresql"; multi-word phrases are collision-safe in text.
            canon = cc.vocab
            amap = dict(cc.alias_pairs)
            job_cat = set()
            for tok in job_flat:
                key = amap.get(tok, tok)
                if key in canon:
                    job_cat.add(key)
            for c in canon:
                if " " in c and c in job_text:
                    job_cat.add(c)
            for alias, c in amap.items():
                if c in canon and " " in alias and alias in job_text:
                    job_cat.add(c)
            cand_cat = set()
            for s in getattr(profile, "all_skills", []):
                key = amap.get(s, s)
                if key in canon:
                    cand_cat.add(key)
        matched = sorted(cand_cat & job_cat)
        all_matched.update(matched); all_job.update(job_cat)
        raw = min(1.0, len(matched)/len(job_cat)) if job_cat else 0.0
        weighted = raw * cc.weight; base += weighted
        cat_scores.append(CategoryScore(cc.code, cc.weight, sorted(cand_cat), sorted(job_cat), matched, round(raw,3), round(weighted,2)))

    exp_bonus = 0
    if exp_min is not None: exp_bonus = 5 if profile.total_years_experience >= exp_min else (2 if profile.total_years_experience >= exp_min*0.75 else 0)
    else: exp_bonus = 3

    if config.embedded_bonus:
        domain_bonus = 5 if any(k in job_text for k in _EMBEDDED_KW) and profile.is_embedded_engineer else 0
    else:
        # Generic domain bonus: the candidate explicitly targets this domain.
        domain_bonus = 5 if target_domains and config.domain_code in target_domains else 0

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
