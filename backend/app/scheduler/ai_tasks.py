"""EMBEDHUNT AI — Scheduled AI maintenance tasks.

Three Celery beat jobs keep the AI layer healthy:

* ``daily_twin_recompute``      — 02:00 daily: refresh scores for active users.
* ``weekly_memory_cleanup``     — 03:00 Sunday: summarise & prune old memories.
* ``daily_review_notifications``— 08:00 daily: nudge users with reviews due.

Each Celery task is a thin synchronous shim that drives an async coroutine with
its own DB session. Service classes and the user-lookup helpers are module-level
so unit tests can patch them and assert the right services are invoked.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct, select

from app.config.logging import get_logger
from app.database.session import AsyncSessionLocal
from app.llm.cost_tracker import AIUsageLog
from app.llm.router import AIRouter
from app.models.user import User
from app.repositories.memory_repository import MemoryRepository
from app.scheduler.celery_app import celery_app
from app.services.adaptive_learning_service import AdaptiveLearningService
from app.services.career_twin_service import CareerTwinService
from app.services.notification_service import NotificationService

logger = get_logger(__name__)


def _run(coro):
    return asyncio.run(coro)


# ── User selection helpers (patchable in tests) ──────────────────────────────
async def get_active_users_last_7_days(session) -> list[str]:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = await session.execute(
        select(distinct(AIUsageLog.user_id)).where(AIUsageLog.created_at >= since)
    )
    return [uid for (uid,) in rows.all() if uid]


async def get_all_users(session) -> list[str]:
    rows = await session.execute(select(User.id).where(User.is_active.is_(True)))
    return [uid for (uid,) in rows.all() if uid]


# ── Task bodies ──────────────────────────────────────────────────────────────
async def _daily_twin_recompute() -> int:
    async with AsyncSessionLocal() as session:
        users = await get_active_users_last_7_days(session)
        service = CareerTwinService(session)
        for user_id in users:
            try:
                await service.recompute_scores(user_id)
            except Exception as exc:  # noqa: BLE001 — one bad user must not stop the run
                logger.warning("twin_recompute_failed", user_id=user_id, error=str(exc))
        await session.commit()
    logger.info("daily_twin_recompute_done", users=len(users))
    return len(users)


async def _weekly_memory_cleanup() -> int:
    async with AsyncSessionLocal() as session:
        memory_repo = MemoryRepository(session, router=AIRouter())
        users = await get_all_users(session)
        for user_id in users:
            try:
                await memory_repo.summarize_old(user_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("memory_summarize_failed", user_id=user_id, error=str(exc))
        try:
            await memory_repo.delete_expired()
        except Exception as exc:  # noqa: BLE001
            logger.warning("memory_delete_expired_failed", error=str(exc))
        await session.commit()
    logger.info("weekly_memory_cleanup_done", users=len(users))
    return len(users)


async def _daily_review_notifications() -> int:
    sent = 0
    async with AsyncSessionLocal() as session:
        adaptive = AdaptiveLearningService(session)
        notifications = NotificationService(session)
        users = await get_active_users_last_7_days(session)
        for user_id in users:
            try:
                queue = await adaptive.get_review_queue(user_id)
                if queue:
                    await notifications.create_review_reminder(user_id, len(queue))
                    sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("review_notification_failed", user_id=user_id, error=str(exc))
        await session.commit()
    logger.info("daily_review_notifications_done", sent=sent)
    return sent


# ── Celery entrypoints ───────────────────────────────────────────────────────
@celery_app.task
def daily_twin_recompute():
    """Run every day at 2am. Recompute scores for all active users."""
    return _run(_daily_twin_recompute())


@celery_app.task
def weekly_memory_cleanup():
    """Run every Sunday at 3am. Summarize and prune old memories."""
    return _run(_weekly_memory_cleanup())


@celery_app.task
def daily_review_notifications():
    """Run every morning at 8am. Send notifications for the review queue."""
    return _run(_daily_review_notifications())


# ── Beat schedule ────────────────────────────────────────────────────────────
def _register_beat_schedule() -> None:
    try:
        from celery.schedules import crontab
    except Exception:  # noqa: BLE001 — stub celery / celery not installed
        return
    celery_app.conf.beat_schedule = {
        "daily-twin-recompute": {
            "task": "app.scheduler.ai_tasks.daily_twin_recompute",
            "schedule": crontab(hour=2, minute=0),
        },
        "weekly-memory-cleanup": {
            "task": "app.scheduler.ai_tasks.weekly_memory_cleanup",
            "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
        },
        "daily-review-notifications": {
            "task": "app.scheduler.ai_tasks.daily_review_notifications",
            "schedule": crontab(hour=8, minute=0),
        },
    }


_register_beat_schedule()
