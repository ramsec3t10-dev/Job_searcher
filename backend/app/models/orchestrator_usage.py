"""EMBEDHUNT AI — Orchestrator AI usage log.

Per-call cost/usage records for the orchestrator's paid engines (hosted open
model and Claude), so cost-per-user is queryable later for the product OKR
tracking. This is intentionally separate from the LLM layer's
``app.llm.cost_tracker.AIUsageLog`` (table ``ai_usage_log``): that one is keyed
by concrete ``model``, whereas this one is keyed by the orchestrator
``engine_used`` label and lives at the routing layer.
"""
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class AiUsageLog(BaseModel):
    __tablename__ = "orchestrator_usage_log"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False, default="")
    task_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    engine_used: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    # Normalised routing tier: rule | kg | cache | hosted | claude. Distinct from
    # engine_used (the concrete model) so the "% by engine / 5%-to-Claude" metric
    # groups cleanly. Every handled request logs one row (free tiers cost 0).
    engine_tier: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Phase 5 telemetry: whether the cheap tier escalated to Claude (a "hard
    # example" signal), and the confidence score of the served answer.
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # created_at / updated_at are provided by BaseModel's TimestampMixin.
