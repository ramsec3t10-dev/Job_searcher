"""EMBEDHUNT AI — Notification Service.

Persists notifications to the ``notifications`` table and serves them to the
in-app feed. Channels other than in-app (email/push) are recorded as not-yet-sent
so a future delivery worker can pick them up.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from app.repositories.notification_repository import NotificationRepository

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    async def _create(
        self,
        user_id: str,
        notif_type: NotificationType,
        title: str,
        body: str,
        *,
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        notification = await self.repo.create(
            user_id=user_id,
            type=notif_type,
            channel=channel,
            title=title,
            body=body,
            action_url=action_url,
            metadata_json=json.dumps(metadata) if metadata else None,
            is_read=False,
            is_sent=(channel == NotificationChannel.IN_APP),
        )
        logger.info(
            "notification_created",
            user_id=user_id,
            type=notif_type.value,
            channel=channel.value,
        )
        return notification

    async def create_job_match_notification(
        self, user_id: str, job_title: str, company: str, score: int
    ) -> dict:
        n = await self._create(
            user_id,
            NotificationType.NEW_JOB_MATCH,
            title=f"New match: {job_title} at {company}",
            body=f"You're a {score}% match for {job_title} at {company}.",
            action_url="/recommendations",
            metadata={"job_title": job_title, "company": company, "score": score},
        )
        return self._serialize(n)

    async def create_review_reminder(self, user_id: str, skill_count: int) -> dict:
        n = await self._create(
            user_id,
            NotificationType.PROFILE_TIP,
            title="Spaced repetition review due",
            body=f"Review {skill_count} skills today to keep them fresh.",
            action_url="/learn/review",
            metadata={"skill_count": skill_count, "reason": "review_due"},
        )
        return self._serialize(n)

    async def create_application_update(
        self, user_id: str, job_title: str, status: str
    ) -> dict:
        n = await self._create(
            user_id,
            NotificationType.APPLICATION_UPDATE,
            title=f"Application update: {job_title}",
            body=f"Your application for {job_title} is now '{status}'.",
            action_url="/applications",
            metadata={"job_title": job_title, "status": status},
        )
        return self._serialize(n)

    async def get_notifications(
        self, user_id: str, *, unread_only: bool = False
    ) -> dict:
        items = await self.repo.get_by_user(user_id, unread_only=unread_only)
        unread = await self.repo.unread_count(user_id)
        return {
            "unread_count": unread,
            "total": len(items),
            "notifications": [self._serialize(n) for n in items],
        }

    async def mark_read(self, user_id: str, notification_id: str) -> dict:
        ok = await self.repo.mark_read(user_id, notification_id)
        return {"updated": ok}

    async def mark_all_read(self, user_id: str) -> dict:
        count = await self.repo.mark_all_read(user_id)
        return {"updated": count}

    @staticmethod
    def _serialize(n: Notification) -> dict:
        return {
            "id": n.id,
            "type": n.type.value,
            "channel": n.channel.value,
            "title": n.title,
            "body": n.body,
            "action_url": n.action_url,
            "metadata": json.loads(n.metadata_json) if n.metadata_json else None,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
