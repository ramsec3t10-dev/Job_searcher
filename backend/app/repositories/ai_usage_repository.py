"""EMBEDHUNT AI — Orchestrator AI-usage analytics (read-only).

Aggregations over ``AiUsageLog`` for the admin cost/routing dashboard: total
spend, split by engine tier (the "5% to Claude" watch metric), and the
highest-cost task types. One row is logged per handled request, so request
percentages are exact.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orchestrator_usage import AiUsageLog

# Every routing tier the orchestrator can attribute a request to.
_TIERS = ("rule", "kg", "cache", "hosted", "claude")


def _month_start(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class AiUsageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def monthly_summary(self, since: Optional[datetime] = None) -> dict:
        """Cost + routing distribution for the period (default: this month)."""
        since = since or _month_start()

        total_requests, total_cost = (
            await self.db.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(AiUsageLog.cost_estimate_usd), 0.0),
                ).where(AiUsageLog.created_at >= since)
            )
        ).one()
        total_requests = int(total_requests)
        total_cost = float(total_cost)

        # By engine tier: requests, %-of-requests, cost, avg latency.
        by_engine: dict[str, dict] = {
            t: {"requests": 0, "pct_requests": 0.0, "cost_usd": 0.0, "avg_latency_ms": 0.0}
            for t in _TIERS
        }
        rows = (
            await self.db.execute(
                select(
                    AiUsageLog.engine_tier,
                    func.count(),
                    func.coalesce(func.sum(AiUsageLog.cost_estimate_usd), 0.0),
                    func.coalesce(func.avg(AiUsageLog.latency_ms), 0.0),
                )
                .where(AiUsageLog.created_at >= since)
                .group_by(AiUsageLog.engine_tier)
            )
        ).all()
        for tier, count, cost, latency in rows:
            count = int(count)
            by_engine[tier or "unknown"] = {
                "requests": count,
                "pct_requests": round(100 * count / total_requests, 2) if total_requests else 0.0,
                "cost_usd": round(float(cost), 6),
                "avg_latency_ms": round(float(latency), 1),
            }

        # Top 10 task types by cost.
        top = (
            await self.db.execute(
                select(
                    AiUsageLog.task_type,
                    func.count(),
                    func.coalesce(func.sum(AiUsageLog.cost_estimate_usd), 0.0),
                )
                .where(AiUsageLog.created_at >= since)
                .group_by(AiUsageLog.task_type)
                .order_by(func.coalesce(func.sum(AiUsageLog.cost_estimate_usd), 0.0).desc())
                .limit(10)
            )
        ).all()
        top_task_types = [
            {"task_type": t, "requests": int(c), "cost_usd": round(float(cost), 6)}
            for t, c, cost in top
        ]

        return {
            "period_start": since.isoformat(),
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 6),
            # The launch KPI: keep this small (target ~5%).
            "claude_pct_requests": by_engine["claude"]["pct_requests"],
            "by_engine": by_engine,
            "top_task_types": top_task_types,
        }
