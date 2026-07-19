"""EMBEDHUNT AI — Career Reasoner.

Turns a candidate profile plus a ranked opportunity set into higher-order,
career-level insights: readiness, market positioning, salary positioning and
the cross-cutting skill gaps that, if closed, would unlock the most value.

Pure and deterministic — operates only on already-computed data structures
(``CandidateProfile`` from the resume pipeline and ``RankingResult`` from the
recommendation engine).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.recommendation.explain import GapPriority
from app.recommendation.ranking import RankingResult
from app.resume.normalizer import CandidateProfile


@dataclass
class CareerInsights:
    candidate: str
    readiness_level: str            # not_ready | emerging | competitive | strong | elite
    readiness_score: int            # 0-99, blended profile + market signal
    is_embedded_engineer: bool
    years_experience: float
    market_position: str            # human-readable positioning statement
    qualified_count: int
    auto_apply_count: int
    strong_count: int
    stretch_count: int
    salary_positioning: str
    top_skill_gaps: list[str] = field(default_factory=list)   # highest-leverage skills to learn
    headline: str = ""
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "readiness_level": self.readiness_level,
            "readiness_score": self.readiness_score,
            "is_embedded_engineer": self.is_embedded_engineer,
            "years_experience": self.years_experience,
            "market_position": self.market_position,
            "qualified_count": self.qualified_count,
            "auto_apply_count": self.auto_apply_count,
            "strong_count": self.strong_count,
            "stretch_count": self.stretch_count,
            "salary_positioning": self.salary_positioning,
            "top_skill_gaps": self.top_skill_gaps,
            "headline": self.headline,
            "rationale": self.rationale,
        }


_READINESS_BANDS = [
    (85, "elite"),
    (70, "strong"),
    (55, "competitive"),
    (40, "emerging"),
    (0, "not_ready"),
]


def _readiness_level(score: int) -> str:
    for threshold, label in _READINESS_BANDS:
        if score >= threshold:
            return label
    return "not_ready"


def _gap_leverage(result: RankingResult) -> list[str]:
    """Rank missing skills by how often + how critically they block good jobs.

    A skill that is a HIGH-priority gap across many strong opportunities is the
    single best thing the candidate can learn next.
    """
    weight: Counter[str] = Counter()
    for job in result.jobs:
        if job.match_score < 50:
            continue
        for gap in job.gap.all_gaps:
            score = {GapPriority.HIGH: 3, GapPriority.MEDIUM: 2, GapPriority.LOW: 1}[gap.priority]
            # Weight by the quality of the job it unblocks.
            score += 1 if job.match_score >= 70 else 0
            weight[gap.skill] += score
    return [skill for skill, _ in weight.most_common(8)]


def reason_about_career(profile: CandidateProfile, result: RankingResult) -> CareerInsights:
    """Produce career-level insights from a profile + ranked opportunities."""
    best = result.jobs[0].match_score if result.jobs else 0
    # Embedded candidates blend their domain score with the best market match
    # (unchanged). For other domains there is no embedded_domain_score signal, so
    # readiness is the best realistic market match.
    if profile.is_embedded_engineer:
        readiness_score = int(round(0.5 * profile.embedded_domain_score + 0.5 * best))
    else:
        readiness_score = best
    level = _readiness_level(readiness_score)

    stretch = sum(1 for j in result.jobs if 55 <= j.match_score < 70)

    if result.auto_apply_count:
        market_position = (
            f"You are a top-tier candidate for {result.auto_apply_count} role(s) right now — "
            f"apply immediately before they close."
        )
    elif result.strong_count:
        market_position = (
            f"You are competitive for {result.strong_count} strong role(s); a small amount of "
            f"targeted prep converts these into offers."
        )
    elif result.total_qualified:
        market_position = (
            f"You qualify for {result.total_qualified} role(s) but most are stretch fits — "
            f"closing a few key gaps will sharply raise your conversion."
        )
    else:
        market_position = "No qualifying roles yet — focus on foundational skills and resume depth."

    # Salary positioning from the best opportunity that also meets the salary bar.
    meets = [j for j in result.jobs if j.meets_salary and j.salary_max_lpa]
    if meets:
        top = max(meets, key=lambda j: j.salary_max_lpa or 0)
        salary_positioning = (
            f"Realistic comp ceiling in reach: up to {top.salary_max_lpa:.0f} LPA "
            f"({top.company})."
        )
    else:
        salary_positioning = "Raise your match scores to unlock roles that meet your salary target."

    top_gaps = _gap_leverage(result)

    if profile.is_embedded_engineer:
        _domain_line = f"Profile domain score {profile.embedded_domain_score}/100; best market match {best}/99."
    else:
        _domain_line = f"Best market match {best}/99 across {result.total_qualified} qualified role(s)."
    rationale = [
        _domain_line,
        f"{result.total_qualified} qualified, {result.auto_apply_count} auto-apply, "
        f"{result.strong_count} strong, {stretch} stretch.",
    ]
    if top_gaps:
        rationale.append(f"Highest-leverage skills to learn: {', '.join(top_gaps[:3])}.")

    headline = (
        f"{level.replace('_', ' ').title()} candidate ({readiness_score}/99). "
        f"{result.auto_apply_count} apply-now, {result.strong_count} strong, {stretch} stretch."
    )

    return CareerInsights(
        candidate=result.candidate,
        readiness_level=level,
        readiness_score=readiness_score,
        is_embedded_engineer=profile.is_embedded_engineer,
        years_experience=profile.total_years_experience,
        market_position=market_position,
        qualified_count=result.total_qualified,
        auto_apply_count=result.auto_apply_count,
        strong_count=result.strong_count,
        stretch_count=stretch,
        salary_positioning=salary_positioning,
        top_skill_gaps=top_gaps,
        headline=headline,
        rationale=rationale,
    )
