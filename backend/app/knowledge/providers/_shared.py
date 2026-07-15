"""Shared helpers for knowledge-layer providers."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_twin import CareerTwin
from app.repositories.career_twin_repository import CareerTwinRepository

_TWIN_STASH_KEY = "career_twin_obj"


async def load_twin(ctx, session: AsyncSession, user_id: str) -> Optional[CareerTwin]:
    """Return the user's Career Twin, reusing the one stashed by CareerTwinProvider.

    Falls back to a fresh query so each provider also works in isolation.
    """
    twin = ctx.stashed(_TWIN_STASH_KEY)
    if twin is not None:
        return twin
    twin = await CareerTwinRepository(session).get_by_user(user_id)
    if twin is not None:
        ctx.stash(_TWIN_STASH_KEY, twin)
    return twin


def current_streak(iso_dates: list[str], today: Optional[date] = None) -> int:
    """Length of the consecutive-day streak ending today or yesterday.

    ``iso_dates`` are ``YYYY-MM-DD`` strings (order-independent, de-duplicated).
    """
    today = today or date.today()
    days = set()
    for raw in iso_dates:
        try:
            days.add(date.fromisoformat(raw))
        except (ValueError, TypeError):
            continue
    if not days:
        return 0
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
