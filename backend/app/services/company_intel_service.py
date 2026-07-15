"""EMBEDHUNT AI — Company intelligence service (profiles + live feedback stats)."""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.company.profiles import CompanyProfile, all_profiles, get_profile
from app.config.logging import get_logger
from app.models.feedback import FeedbackType
from app.orchestrator.gateway import OrchestratorGateway, get_gateway
from app.repositories.feedback_repository import FeedbackEventRepository

logger = get_logger(__name__)

_APPLIED = {FeedbackType.APPLIED.value}
_CALLS = {FeedbackType.SHORTLISTED.value, FeedbackType.INTERVIEW.value, FeedbackType.OFFER.value}
_OFFERS = {FeedbackType.OFFER.value}


class CompanyIntelligenceService:
    def __init__(self, db: AsyncSession, gateway: OrchestratorGateway | None = None):
        self.db = db
        self.feedback_repo = FeedbackEventRepository(db)
        self.gateway = gateway or get_gateway()

    async def get_company_intel(self, name: str) -> dict:
        profile = get_profile(name)
        if profile is None:
            return {"found": False, "message": f"'{name}' not in company intelligence database"}
        stats = await self._success_stats(profile.name)
        return {"found": True, **profile.to_dict(), "application_stats": stats}

    async def summarize(self, name: str, user_id: str | None = None) -> dict:
        """AI summary of a company, routed through the orchestrator.

        ``company_summary`` is on the open-model allowlist, so this is handled by
        the hosted open-model tier (with cache in front and Claude as the
        confidence-gated fallback) — not a direct Claude call.
        """
        profile = get_profile(name)
        if profile is None:
            return {"found": False, "message": f"'{name}' not in company intelligence database"}
        prompt = (
            "Summarize this company for an embedded-systems engineer evaluating it as an "
            "employer, in 3-4 sentences (products, embedded domains, why it's notable):\n"
            f"{json.dumps(profile.to_dict(), default=str)}"
        )
        result = await self.gateway.run(
            "company_summary",
            {"prompt": prompt},
            user_id=user_id,
            session=self.db,
            ground=bool(user_id),  # tailor to the candidate only when we know who they are
        )
        logger.info("company_summary", company=profile.name, engine=result.engine_used)
        return {
            "found": True,
            "company": profile.name,
            "summary": result.text,
            "engine_used": result.engine_used,
            "cached": result.cached,
        }

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
