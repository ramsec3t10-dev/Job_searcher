"""EMBEDHUNT AI — Career Coach.

Synthesises the agent's analysis into human, motivating guidance: what to do
next, which skills to prioritise, and which single role to anchor a learning
roadmap on. This is the "voice" of the copilot.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.agent.decision_engine import AgentAction, Decision
from app.agent.opportunity_finder import OpportunityScan
from app.agent.reasoner import CareerInsights


@dataclass
class CoachingBrief:
    headline: str
    encouragement: str
    next_best_actions: list[str] = field(default_factory=list)
    priority_skills: list[str] = field(default_factory=list)
    roadmap_target_job_id: str | None = None
    roadmap_target_title: str = ""
    interview_target_job_id: str | None = None
    interview_target_title: str = ""

    def to_dict(self) -> dict:
        return {
            "headline": self.headline,
            "encouragement": self.encouragement,
            "next_best_actions": self.next_best_actions,
            "priority_skills": self.priority_skills,
            "roadmap_target_job_id": self.roadmap_target_job_id,
            "roadmap_target_title": self.roadmap_target_title,
            "interview_target_job_id": self.interview_target_job_id,
            "interview_target_title": self.interview_target_title,
        }


_ENCOURAGEMENT = {
    "elite": "You're in the top tier — move fast and apply with confidence.",
    "strong": "You're genuinely competitive. A little focused prep turns these into offers.",
    "competitive": "You're close. Closing a couple of key gaps will sharply lift your results.",
    "emerging": "You have a real foundation. A focused roadmap will open the right doors.",
    "not_ready": "Every strong professional started here. Build the fundamentals and momentum follows.",
}


def _best_with_action(decisions: list[Decision], actions: set[AgentAction]) -> Decision | None:
    candidates = [d for d in decisions if d.action in actions]
    if not candidates:
        return None
    return max(candidates, key=lambda d: (d.confidence, d.match_score))


def coach(
    insights: CareerInsights,
    scan: OpportunityScan,
    decisions: list[Decision],
) -> CoachingBrief:
    """Produce coaching guidance + the anchor jobs for roadmap/interview artifacts."""
    actions: list[str] = []

    if scan.apply_now:
        names = ", ".join(o.company for o in scan.apply_now[:3])
        actions.append(f"Apply now to your top {len(scan.apply_now)} match(es): {names}.")
    if scan.strong:
        actions.append(
            f"Prepare and apply to {len(scan.strong)} strong fit(s) this week."
        )
    if insights.top_skill_gaps:
        actions.append(
            f"Start learning {', '.join(insights.top_skill_gaps[:3])} — they unblock the most roles."
        )
    if not scan.apply_now and not scan.strong:
        actions.append("Anchor on one stretch role and follow its roadmap to close the gap.")

    # Anchor an interview kit on the best apply/strong role.
    interview_target = _best_with_action(
        decisions, {AgentAction.APPLY_NOW, AgentAction.RECOMMEND, AgentAction.INTERVIEW_PREP}
    )
    # Anchor a roadmap on the best near-miss worth investing in.
    roadmap_target = _best_with_action(
        decisions, {AgentAction.UPSKILL_FIRST, AgentAction.STRETCH, AgentAction.INTERVIEW_PREP}
    )

    return CoachingBrief(
        headline=insights.headline,
        encouragement=_ENCOURAGEMENT.get(insights.readiness_level, ""),
        next_best_actions=actions,
        priority_skills=insights.top_skill_gaps,
        roadmap_target_job_id=roadmap_target.job_id if roadmap_target else None,
        roadmap_target_title=roadmap_target.title if roadmap_target else "",
        interview_target_job_id=interview_target.job_id if interview_target else None,
        interview_target_title=interview_target.title if interview_target else "",
    )
