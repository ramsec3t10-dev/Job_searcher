"""EMBEDHUNT AI — LLM cost tracking & budget enforcement.

Persists per-call usage to the ai_usage_log table and exposes rolling cost
aggregations plus a per-user monthly budget check.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, String, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.config.logging import get_logger
from app.config.settings import settings
from app.database.base import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.llm.router import AIResponse

logger = get_logger(__name__)


class AIUsageLog(BaseModel):
    __tablename__ = "ai_usage_log"
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CostTracker:
    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def _sf(self):
        if self._session_factory is not None:
            return self._session_factory
        from app.database.session import AsyncSessionLocal

        return AsyncSessionLocal

    @staticmethod
    def _task_value(response: "AIResponse") -> str:
        task = response.task_type
        return task.value if hasattr(task, "value") else str(task)

    async def track(self, user_id: str, response: "AIResponse", db: "Optional[AsyncSession]" = None) -> AIUsageLog:
        row = AIUsageLog(
            user_id=user_id,
            task_type=self._task_value(response),
            model=response.model_used,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            cached=response.cached,
        )
        if db is not None:
            db.add(row)
            await db.flush()
            return row
        async with self._sf()() as session:
            session.add(row)
            await session.commit()
        return row

    async def _sum(self, user_id: Optional[str], period_days: int, db: "Optional[AsyncSession]") -> float:
        since = datetime.now(timezone.utc) - timedelta(days=period_days)
        stmt = select(func.coalesce(func.sum(AIUsageLog.cost_usd), 0.0)).where(AIUsageLog.created_at >= since)
        if user_id is not None:
            stmt = stmt.where(AIUsageLog.user_id == user_id)
        if db is not None:
            result = await db.execute(stmt)
            return float(result.scalar_one())
        async with self._sf()() as session:
            result = await session.execute(stmt)
            return float(result.scalar_one())

    async def get_user_cost(self, user_id: str, period_days: int = 30, db: "Optional[AsyncSession]" = None) -> float:
        return await self._sum(user_id, period_days, db)

    async def get_total_cost(self, period_days: int = 30, db: "Optional[AsyncSession]" = None) -> float:
        return await self._sum(None, period_days, db)

    async def is_over_budget(
        self, user_id: str, monthly_limit_usd: Optional[float] = None, db: "Optional[AsyncSession]" = None
    ) -> bool:
        limit = monthly_limit_usd if monthly_limit_usd is not None else settings.LLM_MAX_MONTHLY_COST_USD
        return await self.get_user_cost(user_id, 30, db) >= limit
