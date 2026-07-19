"""EMBEDHUNT AI — Action Planner.

Converts per-opportunity decisions plus career insights into a single prioritised
plan of concrete next steps. The plan is what the user actually sees: an ordered,
finite to-do list the copilot is driving on their behalf.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.agent.decision_engine import AgentAction, Decision
from app.agent.reasoner import CareerInsights


class StepKind(str, Enum):
    APPLY = "apply"
    PREP_INTERVIEW = "prep_interview"
    UPSKILL = "upskill"
    REVIEW_STRETCH = "review_stretch"
    IMPROVE_PROFILE = "improve_profile"


# Lower number = higher urgency.
_KIND_ORDER = {
    StepKind.APPLY: 0,
    StepKind.PREP_INTERVIEW: 1,
    StepKind.UPSKILL: 2,
    StepKind.REVIEW_STRETCH: 3,
    StepKind.IMPROVE_PROFILE: 4,
}

_ACTION_TO_KIND = {
    AgentAction.APPLY_NOW: StepKind.APPLY,
    AgentAction.RECOMMEND: StepKind.APPLY,
    AgentAction.INTERVIEW_PREP: StepKind.PREP_INTERVIEW,
    AgentAction.UPSKILL_FIRST: StepKind.UPSKILL,
    AgentAction.STRETCH: StepKind.REVIEW_STRETCH,
}


@dataclass
class PlannedStep:
    order: int
    kind: StepKind
    title: str
    detail: str
    job_id: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "kind": self.kind.value,
            "title": self.title,
            "detail": self.detail,
            "job_id": self.job_id,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ActionPlan:
    steps: list[PlannedStep] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {"steps": [s.to_dict() for s in self.steps], "summary": self.summary, "count": len(self.steps)}


def _step_for_decision(decision: Decision) -> PlannedStep | None:
    kind = _ACTION_TO_KIND.get(decision.action)
    if kind is None:  # SKIP
        return None

    if kind == StepKind.APPLY:
        title = f"Apply to {decision.title} at {decision.company}"
        detail = decision.rationale
    elif kind == StepKind.PREP_INTERVIEW:
        title = f"Prep interview for {decision.title} at {decision.company}"
        detail = decision.rationale
    elif kind == StepKind.UPSKILL:
        gaps = ", ".join(decision.critical_gaps[:3]) or "key skills"
        title = f"Close gaps for {decision.title} ({decision.company})"
        detail = f"Learn {gaps} before applying. {decision.rationale}"
    else:  # REVIEW_STRETCH
        title = f"Build a roadmap toward {decision.title} at {decision.company}"
        detail = decision.rationale

    return PlannedStep(order=0, kind=kind, title=title, detail=detail,
                       job_id=decision.job_id, confidence=decision.confidence)


def build_plan(
    insights: CareerInsights,
    decisions: list[Decision],
    *,
    max_steps: int = 8,
) -> ActionPlan:
    """Order decisions into an actionable plan and prepend any profile work."""
    steps: list[PlannedStep] = []

    # A weak profile blocks everything else — make it the first move.
    if insights.readiness_level in ("not_ready", "emerging") and not insights.auto_apply_count:
        steps.append(PlannedStep(
            order=0, kind=StepKind.IMPROVE_PROFILE,
            title="Strengthen your profile",
            detail=(
                f"Readiness {insights.readiness_score}/99. Add depth on "
                f"{', '.join(insights.top_skill_gaps[:3]) or 'your core target skills'} "
                f"and quantify project impact to unlock more roles."
            ),
            confidence=0.6,
        ))

    for decision in decisions:
        step = _step_for_decision(decision)
        if step is not None:
            steps.append(step)

    # Sort by urgency, then confidence, then match score (confidence encodes score).
    steps.sort(key=lambda s: (_KIND_ORDER[s.kind], -s.confidence))
    steps = steps[:max_steps]
    for i, step in enumerate(steps, 1):
        step.order = i

    n_apply = sum(1 for s in steps if s.kind == StepKind.APPLY)
    n_prep = sum(1 for s in steps if s.kind == StepKind.PREP_INTERVIEW)
    n_up = sum(1 for s in steps if s.kind == StepKind.UPSKILL)
    summary = (
        f"{len(steps)} prioritised action(s): {n_apply} to apply, "
        f"{n_prep} to prep, {n_up} to upskill."
    )

    return ActionPlan(steps=steps, summary=summary)
