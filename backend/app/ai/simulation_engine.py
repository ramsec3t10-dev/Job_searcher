"""EMBEDHUNT AI — Career Simulation Engine (Module 13).

Answers "what-if" questions by cloning the candidate profile, applying a
hypothetical change (learn skills, gain experience, target a role) and
re-running the real matching + salary engines to measure the delta.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from app.ai.salary_intelligence import SalaryIntelligenceEngine
from app.recommendation.engine import run_matching
from app.resume.normalizer import CandidateProfile

# Which CandidateProfile list a simulated skill belongs to.
_SKILL_CATEGORY: dict[str, str] = {
    "autosar": "automotive_safety", "iso 26262": "automotive_safety",
    "asil": "automotive_safety", "functional safety": "automotive_safety",
    "misra c": "automotive_safety", "can": "protocols", "lin": "protocols",
    "flexray": "protocols", "spi": "protocols", "i2c": "protocols",
    "uart": "protocols", "ethernet": "protocols", "someip": "protocols",
    "uds": "protocols", "tcp/ip": "protocols", "mqtt": "protocols",
    "rtos": "rtos_and_os", "freertos": "rtos_and_os", "linux kernel": "rtos_and_os",
    "yocto": "rtos_and_os", "bsp": "rtos_and_os", "c": "programming_languages",
    "c++": "programming_languages", "python": "programming_languages",
    "rust": "programming_languages", "arm": "hardware_platforms",
    "cortex-m": "hardware_platforms", "fpga": "hardware_platforms",
    "risc-v": "hardware_platforms", "device driver": "software_concepts",
    "bootloader": "software_concepts", "bare metal": "software_concepts",
}


def _category_for(skill: str) -> str:
    return _SKILL_CATEGORY.get(skill.strip().lower(), "software_concepts")


@dataclass
class SimulationSnapshot:
    qualified_jobs: int
    auto_apply_jobs: int
    strong_matches: int
    avg_match_score: int
    market_value_max_lpa: float

    def to_dict(self) -> dict:
        return {
            "qualified_jobs": self.qualified_jobs,
            "auto_apply_jobs": self.auto_apply_jobs,
            "strong_matches": self.strong_matches,
            "avg_match_score": self.avg_match_score,
            "market_value_max_lpa": round(self.market_value_max_lpa, 1),
        }


@dataclass
class SimulationResult:
    scenario: str
    baseline: SimulationSnapshot
    projected: SimulationSnapshot
    newly_unlocked_jobs: list[dict] = field(default_factory=list)
    deltas: dict = field(default_factory=dict)
    narrative: str = ""

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "baseline": self.baseline.to_dict(),
            "projected": self.projected.to_dict(),
            "newly_unlocked_jobs": self.newly_unlocked_jobs,
            "deltas": self.deltas,
            "narrative": self.narrative,
        }


class CareerSimulationEngine:
    def __init__(self):
        self.salary = SalaryIntelligenceEngine()

    def _snapshot(self, profile: CandidateProfile, domains, locations) -> tuple[SimulationSnapshot, dict]:
        result = run_matching(profile, min_score=0, salary_min=0.0)
        qualified = [j for j in result.jobs if j.match_score >= 40]
        scores = [j.match_score for j in result.jobs] or [0]
        sal = self.salary.compute(
            years_experience=profile.total_years_experience,
            skill_names=profile.all_skills,
            domains=domains,
            locations=locations,
            current_salary_lpa=0.0,
            dream_companies=[],
        )
        snap = SimulationSnapshot(
            qualified_jobs=len(qualified),
            auto_apply_jobs=result.auto_apply_count,
            strong_matches=result.strong_count,
            avg_match_score=int(sum(scores) / len(scores)),
            market_value_max_lpa=sal.estimated_market_max,
        )
        job_index = {j.job_id: j for j in result.jobs}
        return snap, job_index

    def _augment(self, profile: CandidateProfile, learn_skills: list[str], extra_years: float) -> CandidateProfile:
        clone = copy.deepcopy(profile)
        clone.total_years_experience = round(clone.total_years_experience + extra_years, 1)
        existing = {s.lower() for s in clone.all_skills}
        for skill in learn_skills:
            key = skill.strip().lower()
            if not key or key in existing:
                continue
            existing.add(key)
            clone.all_skills.append(skill)
            getattr(clone, _category_for(skill)).append(skill)
        clone.skill_count = len(clone.all_skills)
        return clone

    def simulate(
        self,
        profile: CandidateProfile,
        *,
        learn_skills: list[str] | None = None,
        extra_years: float = 0.0,
        domains: list[str] | None = None,
        locations: list[str] | None = None,
    ) -> SimulationResult:
        learn_skills = learn_skills or []
        domains = domains or []
        locations = locations or []

        baseline, base_index = self._snapshot(profile, domains, locations)
        projected_profile = self._augment(profile, learn_skills, extra_years)
        projected, proj_index = self._snapshot(projected_profile, domains, locations)

        # Jobs that cross the 40-point qualification line only after the change.
        newly_unlocked = []
        for job_id, pj in proj_index.items():
            bj = base_index.get(job_id)
            if pj.match_score >= 40 and (bj is None or bj.match_score < 40):
                newly_unlocked.append({
                    "job_id": pj.job_id,
                    "title": pj.title,
                    "company": pj.company,
                    "old_score": bj.match_score if bj else 0,
                    "new_score": pj.match_score,
                })
        newly_unlocked.sort(key=lambda x: x["new_score"], reverse=True)

        deltas = {
            "qualified_jobs": projected.qualified_jobs - baseline.qualified_jobs,
            "auto_apply_jobs": projected.auto_apply_jobs - baseline.auto_apply_jobs,
            "strong_matches": projected.strong_matches - baseline.strong_matches,
            "avg_match_score": projected.avg_match_score - baseline.avg_match_score,
            "market_value_max_lpa": round(
                projected.market_value_max_lpa - baseline.market_value_max_lpa, 1
            ),
        }

        scenario = self._describe_scenario(learn_skills, extra_years)
        return SimulationResult(
            scenario=scenario,
            baseline=baseline,
            projected=projected,
            newly_unlocked_jobs=newly_unlocked,
            deltas=deltas,
            narrative=self._narrative(scenario, deltas, newly_unlocked),
        )

    def _describe_scenario(self, learn_skills: list[str], extra_years: float) -> str:
        parts = []
        if learn_skills:
            parts.append("learn " + ", ".join(learn_skills))
        if extra_years:
            parts.append(f"gain {extra_years:g} year(s) experience")
        return "If you " + " and ".join(parts) if parts else "No change"

    def _narrative(self, scenario: str, deltas: dict, unlocked: list[dict]) -> str:
        bits = [f"{scenario}:"]
        if deltas["qualified_jobs"] > 0:
            bits.append(f"+{deltas['qualified_jobs']} qualified jobs")
        if deltas["market_value_max_lpa"] > 0:
            bits.append(f"+{deltas['market_value_max_lpa']} LPA market value")
        if deltas["avg_match_score"] > 0:
            bits.append(f"+{deltas['avg_match_score']} avg match score")
        if unlocked:
            bits.append(f"unlocks {unlocked[0]['company']} ({unlocked[0]['title']})")
        if len(bits) == 1:
            bits.append("no measurable change against the current job corpus.")
        return " ".join(bits)
