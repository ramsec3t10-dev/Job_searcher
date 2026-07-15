"""EMBEDHUNT AI — AI interaction capture (training substrate).

One row per captured AI input/output pair — the raw material for distilling
EMBEDHUNT's own models later. Deliberately separate from the lean
``orchestrator_usage_log`` (cost telemetry): this table holds bulky text plus the
consent, quality and outcome labels that a training pipeline needs, and has its
own retention/governance lifecycle.

DATA GOVERNANCE: rows are written only when capture is explicitly enabled AND
the request carries user consent; ``prompt``/``output`` are PII-scrubbed before
storage. ``role`` distinguishes the answer actually served to the user
(``served``) from a shadow candidate-model answer logged for evaluation but never
shown (``shadow_candidate``).
"""
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class AiInteraction(BaseModel):
    __tablename__ = "ai_interaction"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False, default="")
    task_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    engine_used: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    # "served" | "shadow_candidate"
    role: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="served")
    # For a shadow candidate: the id of the served interaction it shadows.
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)

    # ── the training pair (PII-scrubbed) ────────────────────────────────────
    system: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── provenance / cost ───────────────────────────────────────────────────
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # True when the cheap tier escalated to Claude → a valuable hard example.
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── governance ──────────────────────────────────────────────────────────
    consented: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pii_scrubbed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── quality & outcome labels (attached later via record_feedback) ───────
    accepted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    edited: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    # Downstream outcome, e.g. "applied" | "interview" | "offer" | "dismissed".
    outcome: Mapped[Optional[str]] = mapped_column(String(40), index=True, nullable=True)
