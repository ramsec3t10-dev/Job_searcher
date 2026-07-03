"""EMBEDHUNT AI — Career Simulation Service (Module 13)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.simulation_engine import CareerSimulationEngine
from app.config.logging import get_logger
from app.services.career_twin_service import CareerTwinService
from app.services.profile_service import ProfileService

logger = get_logger(__name__)


class SimulationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_svc = ProfileService(db)
        self.twin_svc = CareerTwinService(db)
        self.engine = CareerSimulationEngine()

    async def simulate(
        self,
        user_id: str,
        *,
        learn_skills: list[str] | None = None,
        extra_years: float = 0.0,
    ) -> dict:
        profile = await self.profile_svc.get_candidate_profile(user_id)
        domains, locations = await self._twin_context(user_id)
        result = self.engine.simulate(
            profile,
            learn_skills=learn_skills,
            extra_years=extra_years,
            domains=domains,
            locations=locations,
        )
        logger.info(
            "career_simulation",
            user_id=user_id,
            learn=learn_skills,
            extra_years=extra_years,
            delta_jobs=result.deltas["qualified_jobs"],
        )
        return result.to_dict()

    async def _twin_context(self, user_id: str) -> tuple[list[str], list[str]]:
        try:
            twin = await self.twin_svc.get_twin(user_id)
            return list(twin.preferred_domains or []), list(twin.preferred_locations or [])
        except Exception:  # noqa: BLE001 — twin optional for simulation
            return [], []
