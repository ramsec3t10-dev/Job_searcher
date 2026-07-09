"""EMBEDHUNT AI — Salary Intelligence Engine (Module 12).

Estimates an engineer's market value from their CareerTwin, identifies which
skills raise it most, and projects a salary trajectory. Pure-compute and
deterministic — no external calls — so it is fully unit-testable.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

# Per-skill annual premium (LPA) commanded in the Indian embedded market.
SKILL_PREMIUM_LPA: dict[str, float] = {
    "iso 26262": 2.5, "functional safety": 2.5, "autosar": 2.0,
    "autosar adaptive": 3.0, "autosar classic": 1.5, "linux kernel": 2.0,
    "device driver": 1.8, "bsp": 1.6, "yocto": 1.5, "can": 1.0, "can-fd": 1.2,
    "canfd": 1.2, "lin": 0.6, "flexray": 1.2, "someip": 1.8, "uds": 1.4,
    "diagnostics": 1.2, "rtos": 1.2, "freertos": 1.0, "rust": 2.5,
    "risc-v": 2.0, "tensorflow lite": 2.0, "tinyml": 2.0, "edge ai": 2.2,
    "adas": 3.0, "sensor fusion": 2.2, "misra c": 1.0, "misra": 1.0,
    "ethernet": 1.0, "tcp/ip": 0.8, "secure boot": 1.8, "cryptography": 1.8,
    "bootloader": 1.2, "arm": 0.8, "cortex-m": 0.8, "cortex-a": 1.2,
    "fpga": 1.6, "verilog": 1.4, "systemverilog": 1.6, "vhdl": 1.4,
    "python": 0.6, "c++": 1.0, "matlab": 0.8, "simulink": 1.4,
    "model based design": 1.4, "pcie": 1.6, "usb": 0.8, "dsp": 1.4,
}

DOMAIN_PREMIUM_LPA: dict[str, float] = {
    "automotive": 1.5, "aerospace": 2.0, "medical": 1.8, "semiconductor": 2.0,
    "industrial": 1.0, "consumer": 0.5, "iot": 1.0, "telecom": 1.2,
}

# City cost/pay multipliers (relative to a national baseline of 1.0).
LOCATION_FACTOR: dict[str, float] = {
    "bangalore": 1.15, "bengaluru": 1.15, "hyderabad": 1.05, "pune": 1.05,
    "chennai": 1.0, "noida": 1.02, "gurugram": 1.08, "gurgaon": 1.08,
    "mumbai": 1.1, "delhi": 1.05, "coimbatore": 0.9, "mysore": 0.9,
    "remote": 1.0,
}

# Company-level pay multipliers applied on top of the market estimate.
COMPANY_FACTOR: dict[str, float] = {
    "qualcomm": 1.35, "nvidia": 1.4, "intel": 1.3, "amd": 1.3, "arm": 1.3,
    "google": 1.6, "apple": 1.6, "microsoft": 1.5, "bosch": 1.15,
    "continental": 1.1, "nxp": 1.2, "texas instruments": 1.25, "ti": 1.25,
    "infineon": 1.2, "harman": 1.1, "kpit": 0.95, "tata elxsi": 1.0,
    "ltts": 0.95, "wipro": 0.9, "tcs": 0.85, "capgemini": 0.9,
}


@dataclass
class SalaryIntelligence:
    current_salary: float
    estimated_market_min: float
    estimated_market_max: float
    percentile: int
    is_underpaid: bool
    underpaid_by_lpa: float
    salary_by_company: dict[str, dict] = field(default_factory=dict)
    top_salary_boosting_skills: list[dict] = field(default_factory=list)
    salary_projection_1yr: float = 0.0
    salary_projection_3yr: float = 0.0
    breakdown: dict = field(default_factory=dict)
    negotiation_tips: list[str] = field(default_factory=list)
    market_reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "current_salary_lpa": round(self.current_salary, 1),
            "estimated_market_min_lpa": round(self.estimated_market_min, 1),
            "estimated_market_max_lpa": round(self.estimated_market_max, 1),
            "market_percentile": self.percentile,
            "is_underpaid": self.is_underpaid,
            "underpaid_by_lpa": round(self.underpaid_by_lpa, 1),
            "salary_by_company": self.salary_by_company,
            "top_salary_boosting_skills": self.top_salary_boosting_skills,
            "salary_projection_1yr_lpa": round(self.salary_projection_1yr, 1),
            "salary_projection_3yr_lpa": round(self.salary_projection_3yr, 1),
            "breakdown": self.breakdown,
            "negotiation_tips": self.negotiation_tips,
            "market_reasoning": self.market_reasoning,
        }


class SalaryIntelligenceEngine:
    """Deterministic market-value estimator driven by CareerTwin fields."""

    def base_by_experience(self, years: float) -> float:
        # Piecewise base compensation curve (LPA) by years of experience.
        if years < 1:
            return 6.0
        if years < 3:
            return 6.0 + (years - 1) * 3.0          # 6 → 12
        if years < 6:
            return 12.0 + (years - 3) * 3.5         # 12 → 22.5
        if years < 10:
            return 22.5 + (years - 6) * 3.0         # 22.5 → 34.5
        return min(60.0, 34.5 + (years - 10) * 2.0)

    def skill_premium(self, skill_names: list[str]) -> float:
        seen: set[str] = set()
        total = 0.0
        for name in skill_names:
            key = name.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            total += SKILL_PREMIUM_LPA.get(key, 0.0)
        # Diminishing returns beyond a point — cap the additive premium.
        return min(total, 12.0)

    def domain_premium(self, domains: list[str]) -> float:
        return max((DOMAIN_PREMIUM_LPA.get(d.lower(), 0.0) for d in domains), default=0.0)

    def location_factor(self, locations: list[str]) -> float:
        factors = [LOCATION_FACTOR.get(l.lower(), 1.0) for l in locations if l]
        return max(factors) if factors else 1.0

    def compute(
        self,
        *,
        years_experience: float,
        skill_names: list[str],
        domains: list[str],
        locations: list[str],
        current_salary_lpa: float,
        dream_companies: list[str],
    ) -> SalaryIntelligence:
        base = self.base_by_experience(years_experience)
        skill_prem = self.skill_premium(skill_names)
        domain_prem = self.domain_premium(domains)
        loc = self.location_factor(locations)

        est_min = (base * 0.85 + skill_prem + domain_prem) * loc
        est_max = (base * 1.15 + skill_prem + domain_prem) * loc

        underpaid = current_salary_lpa > 0 and current_salary_lpa < est_min * 0.9
        underpaid_by = max(0.0, est_min - current_salary_lpa) if current_salary_lpa > 0 else 0.0

        percentile = self._percentile(current_salary_lpa, est_min, est_max)

        by_company = {
            c: self._for_company(c, est_min, est_max) for c in (dream_companies or [])
        }

        boosters = self._salary_boosting_skills(skill_names)

        proj_1 = est_max * 1.12
        proj_3 = est_max * 1.45

        return SalaryIntelligence(
            current_salary=current_salary_lpa,
            estimated_market_min=est_min,
            estimated_market_max=est_max,
            percentile=percentile,
            is_underpaid=underpaid,
            underpaid_by_lpa=underpaid_by,
            salary_by_company=by_company,
            top_salary_boosting_skills=boosters,
            salary_projection_1yr=proj_1,
            salary_projection_3yr=proj_3,
            breakdown={
                "base_lpa": round(base, 1),
                "skill_premium_lpa": round(skill_prem, 1),
                "domain_premium_lpa": round(domain_prem, 1),
                "location_factor": round(loc, 2),
            },
        )

    async def compute_ai(
        self,
        *,
        years_experience: float,
        skill_names: list[str],
        domains: list[str],
        locations: list[str],
        current_salary_lpa: float,
        dream_companies: list[str],
        db,
        user_id: str,
        target_company: str | None = None,
    ) -> SalaryIntelligence:
        """Formula-based ``compute`` enriched with AI negotiation guidance.

        The base figures (min/max/percentile/projections) stay 100% deterministic.
        On success the AI adds ``negotiation_tips`` and ``market_reasoning`` to the
        same response object. Any failure or the toggle being off returns the base
        estimate unchanged.
        """
        base = self.compute(
            years_experience=years_experience,
            skill_names=skill_names,
            domains=domains,
            locations=locations,
            current_salary_lpa=current_salary_lpa,
            dream_companies=dream_companies,
        )
        if not settings.LLM_ENRICHMENT_ENABLED:
            logger.info("salary_intelligence_path", path="fallback", reason="disabled")
            return base
        try:
            from app.agents.salary_agent import SalaryAgent

            ai = await asyncio.wait_for(
                SalaryAgent(db).estimate(user_id, target_company),
                timeout=settings.LLM_ENRICHMENT_TIMEOUT_SECONDS,
            )
            base.negotiation_tips = list(ai.negotiation_tips or [])
            base.market_reasoning = ai.market_reasoning or ""
            logger.info("salary_intelligence_path", path="ai_enriched")
        except Exception as e:  # noqa: BLE001 — enrichment must never break the endpoint
            logger.warning("ai_enrichment_failed", module=__name__, error=str(e))
            return base
        return base

    def _for_company(self, company: str, est_min: float, est_max: float) -> dict:
        factor = COMPANY_FACTOR.get(company.strip().lower(), 1.0)
        return {
            "min_lpa": round(est_min * factor, 1),
            "max_lpa": round(est_max * factor, 1),
            "pay_factor": factor,
        }

    def _percentile(self, current: float, est_min: float, est_max: float) -> int:
        if current <= 0 or est_max <= est_min:
            return 50
        pct = int((current - est_min) / (est_max - est_min) * 100)
        return max(1, min(99, pct))

    def _salary_boosting_skills(self, owned: list[str], top_k: int = 5) -> list[dict]:
        owned_lower = {s.strip().lower() for s in owned}
        candidates = [
            {"skill": name, "premium_lpa": prem}
            for name, prem in SKILL_PREMIUM_LPA.items()
            if name not in owned_lower and prem >= 1.5
        ]
        candidates.sort(key=lambda x: x["premium_lpa"], reverse=True)
        return candidates[:top_k]
