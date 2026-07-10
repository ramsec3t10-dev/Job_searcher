"""EMBEDHUNT AI — AI Analytics & Observability Service.

Read-only aggregations over the ``ai_usage_log`` table (and the Career Twin) for
operational dashboards and per-user insight panels. No LLM calls are made here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.llm.bedrock_client import circuit_state
from app.llm.cost_tracker import AIUsageLog, CostTracker
from app.models.memory import MemoryEntry
from app.repositories.career_twin_repository import CareerTwinRepository

logger = get_logger(__name__)


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _classify_model(model_id: str) -> str:
    m = (model_id or "").lower()
    if "haiku" in m:
        return "haiku"
    if "opus" in m:
        return "opus"
    return "sonnet"


class AIAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.twin_repo = CareerTwinRepository(db)
        self.cost_tracker = CostTracker()

    async def get_system_health(self) -> dict:
        since = _start_of_today()
        rows = (
            await self.db.execute(
                select(AIUsageLog).where(AIUsageLog.created_at >= since)
            )
        ).scalars().all()

        total = len(rows)
        cached = sum(1 for r in rows if r.cached)
        # No explicit error column: a non-cached call that produced no output is
        # treated as a failed/degraded call.
        errors = sum(1 for r in rows if not r.cached and (r.tokens_out or 0) == 0)
        latencies = [r.latency_ms for r in rows if not r.cached and r.latency_ms]
        model_usage = {"haiku": 0, "sonnet": 0, "opus": 0}
        for r in rows:
            model_usage[_classify_model(r.model)] += 1

        return {
            "total_ai_calls_today": total,
            "cache_hit_rate": round(cached / total, 4) if total else 0.0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "total_cost_today_usd": round(sum(r.cost_usd for r in rows), 6),
            "error_rate": round(errors / total, 4) if total else 0.0,
            "model_usage": model_usage,
            "circuit_breaker_status": circuit_state(),
        }

    async def get_user_insights(self, user_id: str) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        twin = await self.twin_repo.get_by_user(user_id)

        calls = (
            await self.db.execute(
                select(func.count())
                .select_from(AIUsageLog)
                .where(AIUsageLog.user_id == user_id, AIUsageLog.created_at >= since)
            )
        ).scalar_one()

        sessions = (
            await self.db.execute(
                select(func.count())
                .select_from(MemoryEntry)
                .where(
                    MemoryEntry.user_id == user_id,
                    MemoryEntry.memory_type == "learning",
                    MemoryEntry.created_at >= since,
                )
            )
        ).scalar_one()

        cost = await self.cost_tracker.get_user_cost(user_id, 30, db=self.db)

        return {
            "twin_last_updated": str(twin.updated_at) if twin else None,
            "skills_added_30d": self._skills_added_30d(twin),
            "sessions_completed_30d": int(sessions),
            "avg_interview_score": float(getattr(twin, "avg_interview_score", 0.0) or 0.0) if twin else 0.0,
            "ai_calls_this_month": int(calls),
            "cost_this_month_usd": round(cost, 6),
            "learning_streak": int(getattr(twin, "learning_streak_days", 0) or 0) if twin else 0,
        }

    @staticmethod
    def _skills_added_30d(twin) -> int:
        if not twin:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).date()
        count = 0
        for entry in twin.skills_learned_this_month or []:
            raw = entry.get("date", "") if isinstance(entry, dict) else ""
            try:
                when = datetime.fromisoformat(raw[:10]).date()
            except (ValueError, TypeError):
                continue
            if when >= cutoff:
                count += 1
        return count
