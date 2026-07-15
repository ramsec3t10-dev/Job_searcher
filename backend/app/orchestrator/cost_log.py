"""EMBEDHUNT AI — Orchestrator cost logging.

Thin persistence helper that writes one :class:`AiUsageLog` row per paid engine
call (hosted open model or Claude). Kept separate from the LLM layer's
``CostTracker`` so the routing layer can bill by ``engine_used`` without coupling
to ``AIResponse``. Callers own the transaction (flush here, commit upstream).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orchestrator_usage import AiUsageLog


async def record_usage(
    session: AsyncSession,
    *,
    user_id: Optional[str],
    task_type: str,
    engine_used: str,
    tokens_in: Optional[int],
    tokens_out: Optional[int],
    cost_estimate_usd: Optional[float],
    engine_tier: str = "",
    latency_ms: Optional[float] = None,
    escalated: bool = False,
    confidence: Optional[float] = None,
) -> AiUsageLog:
    """Insert a usage/cost row for a single handled engine call and return it."""
    row = AiUsageLog(
        user_id=user_id or "",
        task_type=task_type,
        engine_used=engine_used,
        engine_tier=engine_tier,
        latency_ms=float(latency_ms or 0.0),
        tokens_in=int(tokens_in or 0),
        tokens_out=int(tokens_out or 0),
        cost_estimate_usd=float(cost_estimate_usd or 0.0),
        escalated=bool(escalated),
        confidence=confidence,
    )
    session.add(row)
    await session.flush()
    return row
