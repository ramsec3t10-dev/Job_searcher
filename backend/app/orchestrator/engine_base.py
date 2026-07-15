"""EMBEDHUNT AI — Orchestrator engine interface.

Defines the single contract every inference backend implements so the
Orchestrator can treat deterministic rule handlers, the cache, future local
models and Claude interchangeably. An engine either produces an EngineResult or
returns ``None`` to signal "not my job", letting the router fall through to the
next engine in the chain.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class EngineResult(BaseModel):
    """Normalised output of any inference engine.

    A single shape is returned regardless of which backend produced it, so
    callers never need to know whether an answer came from a rule handler, the
    cache or the LLM.

    Attributes:
        text: The engine's textual output.
        engine_used: Identifier of the producing engine (e.g. ``"rule:daily_brief"``
            or ``"claude:claude-sonnet-4-6"``).
        confidence: Optional 0-1 confidence; ``None`` when the engine has no
            meaningful notion of confidence (Claude does not report one).
        cached: ``True`` when the result was served from a cache rather than
            freshly computed.
        cost_estimate_usd: Estimated USD cost of producing the result; ``0.0``
            for deterministic engines, ``None`` when unknown.
        tokens_in: Prompt tokens billed by the model, when known (LLM engines).
        tokens_out: Completion tokens billed by the model, when known.
    """

    text: str
    engine_used: str
    confidence: Optional[float] = None
    cached: bool = False
    cost_estimate_usd: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


class InferenceEngine(ABC):
    """Abstract backend the Orchestrator routes tasks to.

    Implementations return an :class:`EngineResult` when they handle ``task``
    and ``None`` when they cannot, so the router advances to the next engine.
    """

    @abstractmethod
    async def run(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        """Handle ``task`` for ``payload`` or return ``None`` to fall through.

        Args:
            task: Semantic task name (e.g. ``"daily_brief"``, ``"matching"``).
            payload: Task inputs; must be JSON-serialisable so it can be cached.
            context: Optional per-request metadata (user id, cache flags, …).

        Returns:
            An :class:`EngineResult` if this engine handled the task, otherwise
            ``None`` to let the Orchestrator try the next engine.
        """
        ...
