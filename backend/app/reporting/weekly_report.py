"""EMBEDHUNT AI — Weekly Career Report (Module 14).

Composes the outputs of existing engines (Career Twin delta, recommendations,
salary intelligence) into a single weekly digest. Pure aggregation/formatting —
each data source is fetched by the service and passed in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class WeeklyReport:
    generated_at: str
    headline: str
    scores: dict = field(default_factory=dict)
    whats_changed: list[dict] = field(default_factory=list)
    job_market: dict = field(default_factory=dict)
    salary: dict = field(default_factory=dict)
    focus_this_week: list[str] = field(default_factory=list)
    digest: str = ""

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "headline": self.headline,
            "scores": self.scores,
            "whats_changed": self.whats_changed,
            "job_market": self.job_market,
            "salary": self.salary,
            "focus_this_week": self.focus_this_week,
            "digest": self.digest,
        }


def build_weekly_report(
    *,
    full_name: str,
    weekly_delta: dict,
    recommendations: dict,
    salary: dict | None,
    known_weaknesses: list[str],
) -> WeeklyReport:
    scores = weekly_delta.get("current_scores", {})
    changed = weekly_delta.get("changed_fields", [])

    qualified = recommendations.get("total_qualified", 0)
    strong = recommendations.get("strong_count", 0)
    auto = recommendations.get("auto_apply_count", 0)
    top_jobs = [
        {"title": j["title"], "company": j["company"], "match_score": j["match_score"]}
        for j in recommendations.get("jobs", [])[:3]
    ]

    focus: list[str] = []
    for w in known_weaknesses[:3]:
        focus.append(f"Improve confidence in {w}")
    if auto > 0:
        focus.append(f"Review and approve {auto} auto-apply-ready job(s)")
    if salary and salary.get("is_underpaid"):
        focus.append(
            f"You appear underpaid by ~{salary['underpaid_by_lpa']} LPA — see the negotiation brief"
        )
    if not focus:
        focus.append("Keep your Career Twin fresh — log any new skills or interviews")

    headline = (
        f"{qualified} qualified role(s) this week"
        + (f", {strong} strong match(es)" if strong else "")
        + (f", {len(changed)} profile update(s)" if changed else "")
    )

    salary_section = {}
    if salary:
        salary_section = {
            "market_min_lpa": salary.get("estimated_market_min_lpa"),
            "market_max_lpa": salary.get("estimated_market_max_lpa"),
            "market_percentile": salary.get("market_percentile"),
            "is_underpaid": salary.get("is_underpaid"),
        }

    digest = _digest(full_name, headline, top_jobs, focus)

    return WeeklyReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        headline=headline,
        scores=scores,
        whats_changed=changed,
        job_market={
            "qualified_jobs": qualified,
            "strong_matches": strong,
            "auto_apply_ready": auto,
            "top_jobs": top_jobs,
        },
        salary=salary_section,
        focus_this_week=focus,
        digest=digest,
    )


def _digest(name: str, headline: str, top_jobs: list[dict], focus: list[str]) -> str:
    greeting = f"Hi {name}," if name else "Hi,"
    lines = [greeting, f"Your week in one line: {headline}."]
    if top_jobs:
        best = top_jobs[0]
        lines.append(f"Top match: {best['title']} at {best['company']} ({best['match_score']}%).")
    if focus:
        lines.append("This week, focus on: " + "; ".join(focus) + ".")
    return " ".join(lines)
