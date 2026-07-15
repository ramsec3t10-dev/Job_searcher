"""EMBEDHUNT AI — Training dataset export.

Turns captured :class:`AiInteraction` rows into fine-tuning-ready examples,
with the filters a distillation run needs (consent, quality, teacher-only, …).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_interaction import AiInteraction


def _to_example(row: AiInteraction) -> dict:
    messages = []
    if row.system:
        messages.append({"role": "system", "content": row.system})
    messages.append({"role": "user", "content": row.prompt})
    return {
        "task": row.task_type,
        "messages": messages,
        "completion": row.output,
        "meta": {
            "engine": row.engine_used,
            "confidence": row.confidence,
            "escalated": row.escalated,
            "accepted": row.accepted,
            "rating": row.rating,
            "outcome": row.outcome,
        },
    }


async def export_task(
    session: AsyncSession,
    task: str,
    *,
    role: str = "served",
    consented_only: bool = True,
    teacher_only: bool = False,
    exclude_rejected: bool = True,
    limit: Optional[int] = None,
) -> list[dict]:
    """Export captured examples for ``task`` as ``[{messages, completion, meta}]``.

    Args:
        role: ``"served"`` (default) or ``"shadow_candidate"``.
        consented_only: only rows the user consented to (governance default on).
        teacher_only: only frontier/Claude answers — the highest-quality targets.
        exclude_rejected: drop rows explicitly marked ``accepted=False``.
        limit: cap the number of rows.
    """
    stmt = select(AiInteraction).where(
        AiInteraction.task_type == task, AiInteraction.role == role
    )
    if consented_only:
        stmt = stmt.where(AiInteraction.consented == True)  # noqa: E712
    if teacher_only:
        stmt = stmt.where(AiInteraction.engine_used.like("claude:%"))
    if exclude_rejected:
        stmt = stmt.where(AiInteraction.accepted.isnot(False))  # keeps NULL + True
    stmt = stmt.order_by(AiInteraction.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_example(r) for r in rows]


async def dataset_stats(session: AsyncSession, task: str) -> dict:
    """Quick counts for a task's captured data (for a distillation dashboard)."""
    async def _count(*conds) -> int:
        stmt = select(func.count()).select_from(AiInteraction).where(
            AiInteraction.task_type == task, *conds
        )
        return int((await session.execute(stmt)).scalar_one())

    served = await _count(AiInteraction.role == "served")
    shadow = await _count(AiInteraction.role == "shadow_candidate")
    escalated = await _count(AiInteraction.role == "served", AiInteraction.escalated == True)  # noqa: E712
    accepted = await _count(AiInteraction.role == "served", AiInteraction.accepted == True)  # noqa: E712
    return {
        "task": task,
        "served": served,
        "shadow_candidates": shadow,
        "escalated_hard_examples": escalated,
        "accepted": accepted,
    }
