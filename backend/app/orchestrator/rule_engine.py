"""EMBEDHUNT AI — Deterministic rule engine.

A registry of plain-Python handlers keyed by task name. Handlers are pure,
zero-LLM functions that build a result directly from the payload, so
deterministic work never pays for (or waits on) a model call. Tasks with no
registered handler return ``None`` so the Orchestrator falls through to the next
engine.

Two handlers ship as working examples:

* ``daily_brief`` — renders a personalised morning brief from a payload dict.
* ``flashcard_schedule`` — computes the next spaced-repetition interval (SM-2).
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from app.config.logging import get_logger
from app.orchestrator.engine_base import EngineResult, InferenceEngine

logger = get_logger(__name__)

# A rule handler maps (payload, context) -> plain text. Registered by task name.
RuleHandler = Callable[[dict, dict], str]


class RuleEngine(InferenceEngine):
    """Deterministic engine backed by a ``task name -> handler`` registry."""

    def __init__(self, register_defaults: bool = True):
        self._handlers: dict[str, RuleHandler] = {}
        if register_defaults:
            self.register("daily_brief", _daily_brief)
            self.register("flashcard_schedule", _flashcard_schedule)

    def register(self, task: str, handler: RuleHandler) -> None:
        """Register (or replace) the handler for ``task``."""
        self._handlers[task] = handler

    def unregister(self, task: str) -> None:
        """Remove the handler for ``task`` if present."""
        self._handlers.pop(task, None)

    def handles(self, task: str) -> bool:
        """Return whether a handler is registered for ``task``."""
        return task in self._handlers

    async def run(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        """Run the registered handler for ``task`` or return ``None``."""
        handler = self._handlers.get(task)
        if handler is None:
            return None
        text = handler(payload, context or {})
        logger.info("orchestrator_rule_engine", task=task)
        return EngineResult(
            text=text,
            engine_used=f"rule:{task}",
            confidence=1.0,
            cached=False,
            cost_estimate_usd=0.0,
        )


def _daily_brief(payload: dict, context: dict) -> str:
    """Render a personalised daily brief from the payload — no LLM involved."""
    name = payload.get("name", "there")
    streak = int(payload.get("streak_days", 0))
    new_matches = int(payload.get("new_matches", 0))
    pending = int(payload.get("pending_applications", 0))
    focus = payload.get("focus", "Keep making steady progress on your search.")
    day = "day" if streak == 1 else "days"
    lines = [
        f"Good morning, {name}!",
        f"🔥 Streak: {streak} {day}.",
        f"🎯 New matches waiting for review: {new_matches}.",
        f"📮 Applications pending action: {pending}.",
        f"👉 Today's focus: {focus}",
    ]
    return "\n".join(lines)


def _flashcard_schedule(payload: dict, context: dict) -> str:
    """Compute the next spaced-repetition interval (simplified SM-2).

    Reads the recall ``quality`` (0-5 grade) plus the prior ``repetitions``,
    ``ease_factor`` and ``interval_days`` from the payload and returns the next
    schedule as a JSON string. Pure arithmetic — no model call.

    A grade below 3 resets the card to the start of the ladder (review again in
    one day); grades of 3+ advance it (1 day, then 6 days, then previous
    interval scaled by the ease factor) and nudge the ease factor.
    """
    quality = int(payload.get("quality", 0))
    repetitions = int(payload.get("repetitions", 0))
    ease = float(payload.get("ease_factor", 2.5))
    interval = int(payload.get("interval_days", 0))

    if quality < 3:
        repetitions = 0
        next_interval = 1
    else:
        if repetitions == 0:
            next_interval = 1
        elif repetitions == 1:
            next_interval = 6
        else:
            next_interval = round(interval * ease)
        repetitions += 1

    # SM-2 ease-factor update, clamped to the canonical 1.3 floor.
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(1.3, round(ease, 2))

    return json.dumps(
        {
            "repetitions": repetitions,
            "ease_factor": ease,
            "interval_days": next_interval,
            "next_review_in_days": next_interval,
        }
    )
