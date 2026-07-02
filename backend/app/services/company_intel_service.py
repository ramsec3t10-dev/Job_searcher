"""EMBEDHUNT AI — Company intelligence service (profiles + live feedback stats)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.company.profiles import CompanyProfile, all_profiles, get_profile
from app.models.feedback import FeedbackType
from app.repositories.feedback_repository import FeedbackEventRepository

_APPLIED = {FeedbackType.APPLIED.value}
_CALLS = {FeedbackType.SHORTLISTED.value, FeedbackType.INTERVIEW.value, FeedbackType.OFFER.value}
_OFFERS = {FeedbackType.OFFER.value}


class CompanyIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.feedback_repo = FeedbackEventRepository(db)

    async def get_company_intel(self, name: str) -> dict:
        profile = get_profile(name)
        if profile is None:
            return {"found": False, "message": f"'{name}' not in company intelligence database"}
        stats = await self._success_stats(profile.name)
        return {"found": True, **profile.to_dict(), "application_stats": stats}

    async def list_companies(self, tier: str | None = None, limit: int = 60) -> dict:
        profiles = all_profiles()
        if tier:
            profiles = [p for p in profiles if p.tier == tier]
        items = [p.to_dict() for p in profiles[:limit]]
        return {"total": len(profiles), "companies": items}

    async def _success_stats(self, company: str) -> dict:
        events = await self.feedback_repo.list_for_company(company)
        applied = sum(1 for e in events if e.feedback_type in _APPLIED)
        calls = sum(1 for e in events if e.feedback_type in _CALLS)
        offers = sum(1 for e in events if e.feedback_type in _OFFERS)
        denom = applied or None
        return {
            "applications": applied,
            "calls": calls,
            "offers": offers,
            "call_rate": round(calls / denom, 3) if denom else 0.0,
            "offer_rate": round(offers / denom, 3) if denom else 0.0,
        }
