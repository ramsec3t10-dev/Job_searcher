"""EMBEDHUNT AI — Weekly Report Service (Module 14)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.reporting.weekly_report import build_weekly_report
from app.services.career_twin_service import CareerTwinService
from app.services.recommendation_service import RecommendationService
from app.services.salary_service import SalaryService

logger = get_logger(__name__)


class WeeklyReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_svc = CareerTwinService(db)
        self.rec_svc = RecommendationService(db)
        self.salary_svc = SalaryService(db)

    async def generate(self, user_id: str) -> dict:
        full_name = ""
        weekly_delta: dict = {"current_scores": {}, "changed_fields": []}
        known_weaknesses: list[str] = []
        salary: dict | None = None

        try:
            twin = await self.twin_svc.get_twin(user_id)
            full_name = twin.full_name or ""
            known_weaknesses = list(twin.known_weaknesses or [])
            weekly_delta = await self.twin_svc.get_weekly_delta(user_id)
            salary = await self.salary_svc.get_intelligence(user_id)
        except Exception as exc:  # noqa: BLE001 — report still useful without a twin
            logger.info("weekly_report_no_twin", user_id=user_id, error=str(exc))

        try:
            recommendations = await self.rec_svc.get_recommendations(user_id)
        except Exception:  # noqa: BLE001
            recommendations = {"total_qualified": 0, "strong_count": 0, "auto_apply_count": 0, "jobs": []}

        report = build_weekly_report(
            full_name=full_name,
            weekly_delta=weekly_delta,
            recommendations=recommendations,
            salary=salary,
            known_weaknesses=known_weaknesses,
        )
        logger.info("weekly_report_generated", user_id=user_id)
        return report.to_dict()
