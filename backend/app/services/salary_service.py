"""EMBEDHUNT AI — Salary Intelligence Service (Module 12).

Bridges the CareerTwin (source of truth) to the deterministic salary engine.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.salary_intelligence import SalaryIntelligenceEngine
from app.config.logging import get_logger
from app.services.career_twin_service import CareerTwinService

logger = get_logger(__name__)


class SalaryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_svc = CareerTwinService(db)
        self.engine = SalaryIntelligenceEngine()

    async def get_intelligence(self, user_id: str) -> dict:
        twin = await self.twin_svc.get_twin(user_id)
        skill_names = [s.get("name", "") for s in (twin.skills or []) if s.get("name")]
        result = await self.engine.compute_ai(
            years_experience=twin.total_years_experience or 0.0,
            skill_names=skill_names,
            domains=list(twin.preferred_domains or []),
            locations=list(twin.preferred_locations or []),
            current_salary_lpa=twin.current_salary_lpa or 0.0,
            dream_companies=list(twin.dream_companies or []),
            db=self.db,
            user_id=user_id,
        )
        logger.info(
            "salary_intelligence_computed",
            user_id=user_id,
            percentile=result.percentile,
            underpaid=result.is_underpaid,
        )
        return result.to_dict()

    async def negotiation_brief(self, user_id: str) -> dict:
        """A concise, actionable brief the candidate can use in negotiations."""
        intel = await self.get_intelligence(user_id)
        talking_points: list[str] = []
        if intel["is_underpaid"]:
            talking_points.append(
                f"You are ~{intel['underpaid_by_lpa']} LPA below the market floor "
                f"for your experience and skill set."
            )
        talking_points.append(
            f"Market range for your profile: {intel['estimated_market_min_lpa']}–"
            f"{intel['estimated_market_max_lpa']} LPA."
        )
        if intel["top_salary_boosting_skills"]:
            top = intel["top_salary_boosting_skills"][0]
            talking_points.append(
                f"Learning {top['skill']} could add ~{top['premium_lpa']} LPA to your market value."
            )
        return {
            "target_ask_lpa": intel["estimated_market_max_lpa"],
            "walk_away_floor_lpa": intel["estimated_market_min_lpa"],
            "market_percentile": intel["market_percentile"],
            "talking_points": talking_points,
            "salary_by_company": intel["salary_by_company"],
        }
