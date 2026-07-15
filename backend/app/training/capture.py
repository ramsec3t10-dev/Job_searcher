"""EMBEDHUNT AI — Training data capture hook.

Injected into the Orchestrator. For each *paid* engine result it writes a
PII-scrubbed, consent-gated :class:`AiInteraction` row (the served answer), and —
when shadow routing is on — also runs a candidate model and logs its answer
(role ``shadow_candidate``) **without serving it**.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.config.settings import settings
from app.models.ai_interaction import AiInteraction
from app.orchestrator.hosted_model_engine import scrub_pii

logger = get_logger(__name__)


def _prompt_text(payload: dict) -> str:
    """Reconstruct the user-facing prompt text from a payload for storage."""
    for key in ("prompt", "input", "query", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        joined = "\n".join(
            m.get("content", "") for m in messages if isinstance(m, dict) and m.get("content")
        )
        if joined.strip():
            return joined
    return json.dumps(
        {k: v for k, v in payload.items() if k not in ("system", "max_tokens")},
        sort_keys=True, default=str,
    )


class TrainingCapture:
    """Persists served + shadow interactions for later distillation."""

    def __init__(self, shadow_engine=None):
        self._shadow = shadow_engine

    async def on_result(self, context: dict, task: str, payload: dict, result, *, escalated: bool = False) -> None:
        """Capture a served engine result (best-effort; never raises upstream)."""
        if not settings.ORCHESTRATOR_CAPTURE_TRAINING_DATA:
            return
        session = context.get("db")
        if session is None:
            return  # need a session to persist
        # DATA GOVERNANCE: never capture without explicit per-request consent.
        if not bool(context.get("consent", False)):
            return
        try:
            served = await self._write(
                session, role="served", parent_id=None,
                user_id=context.get("user_id"), task=task, payload=payload, result=result,
                escalated=escalated,
            )
        except Exception as exc:  # noqa: BLE001 — capture must never break a request
            logger.warning("training_capture_failed", task=task, error=str(exc))
            return

        if self._shadow is not None and settings.ORCHESTRATOR_SHADOW_MODEL_ENABLED:
            try:
                candidate = await self._shadow.generate(task, payload, context)
                if candidate is not None:
                    await self._write(
                        session, role="shadow_candidate", parent_id=served.id,
                        user_id=context.get("user_id"), task=task, payload=payload, result=candidate,
                        escalated=False,
                    )
            except Exception as exc:  # noqa: BLE001 — shadow is best-effort, log-only
                logger.warning("shadow_capture_failed", task=task, error=str(exc))

    async def _write(
        self, session: AsyncSession, *, role: str, parent_id: Optional[str],
        user_id: Optional[str], task: str, payload: dict, result, escalated: bool,
    ) -> AiInteraction:
        raw_system = payload.get("system") or ""
        row = AiInteraction(
            user_id=user_id or "",
            task_type=task,
            engine_used=result.engine_used,
            role=role,
            parent_id=parent_id,
            system=scrub_pii(raw_system) or None,
            prompt=scrub_pii(_prompt_text(payload)),
            output=scrub_pii(result.text or ""),
            tokens_in=int(result.tokens_in or 0),
            tokens_out=int(result.tokens_out or 0),
            cost_estimate_usd=float(result.cost_estimate_usd or 0.0),
            confidence=result.confidence,
            escalated=bool(escalated),
            consented=True,
            pii_scrubbed=True,
        )
        session.add(row)
        await session.flush()
        return row


async def record_feedback(
    session: AsyncSession,
    interaction_id: str,
    *,
    accepted: Optional[bool] = None,
    edited: Optional[bool] = None,
    rating: Optional[int] = None,
    outcome: Optional[str] = None,
) -> Optional[AiInteraction]:
    """Attach quality/outcome labels to a captured interaction (called later).

    Services call this when the user accepts/edits an answer, or when a
    downstream outcome (applied → interview → offer) resolves — turning raw
    captures into *labelled* training/eval data.
    """
    row = await session.get(AiInteraction, interaction_id)
    if row is None:
        return None
    if accepted is not None:
        row.accepted = accepted
    if edited is not None:
        row.edited = edited
    if rating is not None:
        row.rating = int(rating)
    if outcome is not None:
        row.outcome = outcome
    await session.flush()
    return row


def build_capture() -> Optional[TrainingCapture]:
    """Build a TrainingCapture from settings, or ``None`` when capture is off."""
    if not settings.ORCHESTRATOR_CAPTURE_TRAINING_DATA:
        return None
    shadow = None
    if settings.ORCHESTRATOR_SHADOW_MODEL_ENABLED:
        from app.training.shadow import build_shadow_engine

        shadow = build_shadow_engine()
    return TrainingCapture(shadow_engine=shadow)
