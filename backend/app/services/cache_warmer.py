"""EMBEDHUNT AI — login cache warming.

Runs as a fire-and-forget background task right after login so the first screen
the user opens is already populated:

  * daily brief   (mentor)   — only if not already cached
  * salary estimate          — only if not already cached
  * top job matches          — pure compute, no LLM cost

Everything is best-effort and budget-aware: brief/salary warming is skipped when
enrichment is disabled or the user is over their monthly budget, so warming can
never itself blow the budget or break the login flow.
"""
from __future__ import annotations

from app.config.logging import get_logger
from app.config.settings import settings
from app.database.session import AsyncSessionLocal
from app.llm.cost_tracker import CostTracker

logger = get_logger(__name__)

# Precomputed top matches, keyed by user_id, read by the matches endpoint/insights.
_matches_cache: dict[str, list[dict]] = {}


def get_warm_matches(user_id: str) -> list[dict] | None:
    return _matches_cache.get(user_id)


async def warm_user_caches(user_id: str) -> None:
    """Warm per-user caches. Never raises — logs and returns on any failure."""
    try:
        async with AsyncSessionLocal() as db:
            await _warm_matches(db, user_id)
            if not settings.LLM_ENRICHMENT_ENABLED:
                return
            if await CostTracker().is_over_budget(user_id, db=db):
                return
            await _warm_daily_brief(db, user_id)
            await _warm_salary(db, user_id)
    except Exception as exc:  # noqa: BLE001 — warming is strictly best-effort
        logger.warning("cache_warm_failed", user_id=user_id, error=str(exc))


async def _warm_daily_brief(db, user_id: str) -> None:
    from app.api.v1.ai_features import _brief_cache

    if _brief_cache.get(user_id) is not None:
        return
    try:
        from app.agents.mentor_agent import MentorAgent

        brief = await MentorAgent(db).daily_brief(user_id)
        _brief_cache.set(user_id, brief.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.warning("warm_brief_failed", user_id=user_id, error=str(exc))


async def _warm_salary(db, user_id: str) -> None:
    from app.api.v1.ai_features import _salary_cache

    key = f"{user_id}:"
    if _salary_cache.get(key) is not None:
        return
    try:
        from app.agents.salary_agent import SalaryAgent

        result = await SalaryAgent(db).estimate(user_id, None)
        _salary_cache.set(key, result.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.warning("warm_salary_failed", user_id=user_id, error=str(exc))


async def _warm_matches(db, user_id: str) -> None:
    try:
        from app.recommendation.engine import run_matching
        from app.repositories.career_twin_repository import CareerTwinRepository
        from app.services.adaptive_learning_service import AdaptiveLearningService

        twin = await CareerTwinRepository(db).get_by_user(user_id)
        if twin is None:
            return
        profile = AdaptiveLearningService(db)._twin_to_profile(twin)
        result = run_matching(profile, min_score=0)
        _matches_cache[user_id] = [
            j.model_dump() if hasattr(j, "model_dump") else dict(j)
            for j in (getattr(result, "jobs", None) or [])[:5]
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("warm_matches_failed", user_id=user_id, error=str(exc))
