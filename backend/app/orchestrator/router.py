"""EMBEDHUNT AI — AI Orchestrator.

The single routing layer every AI-needing service calls instead of hitting
Bedrock directly. A task is offered to each engine in a fixed fallthrough order
until one returns a result:

    rule_engine → knowledge_graph_engine → cache_engine (exact match)
        → hosted_model_engine (Together AI, gated) → claude_engine

Every fresh (non-cached) result produced downstream of the cache is written back
to the cache before returning, and the engine that handled each request is
logged. Rule-engine and knowledge-graph results sit *before* the cache: they are
deterministic and free, so they are intentionally recomputed rather than cached.
The knowledge-graph engine signals "not my query" by returning ``confidence=None``
(or ``None``); routing then continues to fall through as before.

The hosted open-model engine (Phase 3) is only attempted for tasks on the
allowlist in :mod:`app.orchestrator.task_registry`; a low-confidence hosted
answer returns ``confidence=None`` and escalates to Claude. Every paid engine
call (hosted or Claude) is cost-logged to the ``AiUsageLog`` table when a DB
session is available (``context["db"]`` or an injected ``usage_session_factory``).
"""
from __future__ import annotations

import time
from typing import Optional

from app.config.logging import get_logger
from app.config.settings import settings
from app.core.exceptions import EmbedHuntException
from app.orchestrator.cache_engine import CacheEngine
from app.orchestrator.claude_engine import ClaudeEngine
from app.orchestrator.cost_log import record_usage
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.hosted_model_engine import HostedModelEngine
from app.orchestrator.knowledge_graph_engine import KnowledgeGraphEngine
from app.orchestrator.rule_engine import RuleEngine
from app.orchestrator.task_registry import is_hosted_allowed

logger = get_logger(__name__)


class OrchestratorError(EmbedHuntException):
    """Raised when no engine in the chain can handle a task."""

    def __init__(self, message: str):
        super().__init__(message, 502)


class Orchestrator:
    """Routes AI tasks through the engine chain with cache write-back.

    Engines are injectable so tests can supply mocks and later phases can swap
    implementations without touching call sites.
    """

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        knowledge_graph_engine: Optional[KnowledgeGraphEngine] = None,
        cache_engine: Optional[CacheEngine] = None,
        hosted_model_engine: Optional[HostedModelEngine] = None,
        claude_engine: Optional[ClaudeEngine] = None,
        usage_session_factory=None,
        capture=None,
    ):
        self.rule_engine = rule_engine or RuleEngine()
        self.knowledge_graph_engine = knowledge_graph_engine or KnowledgeGraphEngine()
        self.cache_engine = cache_engine or CacheEngine()
        self.hosted_model_engine = hosted_model_engine or HostedModelEngine()
        self.claude_engine = claude_engine or ClaudeEngine()
        self._cache_enabled = getattr(settings, "ORCHESTRATOR_ENABLE_CACHE", True)
        self._hosted_enabled = getattr(settings, "ORCHESTRATOR_ENABLE_HOSTED_MODEL", True)
        # Optional factory for cost logging when a request carries no db session.
        # Left None by default so unit tests never open a real DB connection;
        # the app composition root can inject AsyncSessionLocal to always persist.
        self._usage_session_factory = usage_session_factory
        # Optional TrainingCapture (Phase 5). None → no capture; when present it
        # self-gates on settings + per-request consent (see app.training.capture).
        self._capture = capture

    async def handle(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> EngineResult:
        """Route ``task`` through the engine chain and return the first result.

        Args:
            task: Semantic task name (e.g. ``"daily_brief"``, ``"matching"``).
            payload: Task inputs; must be JSON-serialisable so it can be cached.
            context: Optional per-request metadata (user id, cache flags, …).

        Returns:
            The :class:`EngineResult` from whichever engine handled the task.

        Raises:
            OrchestratorError: If no engine in the chain produced a result.
        """
        context = context or {}
        start = time.perf_counter()

        # 1) Deterministic rule handlers — zero cost, never reach the LLM.
        result = await self.rule_engine.run(task, payload, context)
        if result is not None:
            return await self._serve(context, task, payload, result, tier="rule", start=start)

        # 2) Knowledge graph — deterministic skill/role graph answers, zero LLM.
        #    A confidence=None result (or None) means "not my query" → fall through.
        kg_result = await self.knowledge_graph_engine.run(task, payload, context)
        if kg_result is not None and kg_result.confidence is not None:
            return await self._serve(context, task, payload, kg_result, tier="kg", start=start)

        # 3) Cache — exact match, then semantic (embedding-similarity) recall.
        if self._cache_enabled:
            cached = await self.cache_engine.run(task, payload, context)
            if cached is not None:
                return await self._serve(context, task, payload, cached, tier="cache", start=start)

        # 4) Hosted open-model engine (Together AI) — mid-tier, before Claude.
        #    Gated by the task allowlist so Claude-only tasks never reach it.
        #    A low-confidence answer returns confidence=None → escalate to Claude.
        escalated = False
        if self._hosted_enabled and is_hosted_allowed(task):
            hosted = await self.hosted_model_engine.run(task, payload, context)
            if hosted is not None:
                if hosted.confidence is not None:
                    return await self._serve(
                        context, task, payload, hosted, tier="hosted",
                        start=start, capture=True, writeback=True,
                    )
                # Low confidence: bill the (unserved) call, then escalate to Claude.
                await self._log_usage(
                    context, task, hosted, tier="hosted",
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                )
                escalated = True  # cheap tier failed → a hard example for training
                logger.info("orchestrator_hosted_escalated", task=task)

        # 5) Claude (AWS Bedrock) — the terminal engine.
        result = await self.claude_engine.run(task, payload, context)
        if result is None:
            raise OrchestratorError(f"No engine could handle task '{task}'")
        return await self._serve(
            context, task, payload, result, tier="claude",
            start=start, escalated=escalated, capture=True, writeback=True,
        )

    @staticmethod
    def _tier_cost(tier: str, result: EngineResult) -> float:
        """Marginal cost of a served result. Free/replay tiers cost 0 regardless
        of the (original) cost stored on a cached result."""
        return float(result.cost_estimate_usd or 0.0) if tier in ("hosted", "claude") else 0.0

    async def _serve(
        self, context: dict, task: str, payload: dict, result: EngineResult, *,
        tier: str, start: float, escalated: bool = False,
        capture: bool = False, writeback: bool = False,
    ) -> EngineResult:
        """Finalise a served result: optional cache write-back, usage logging,
        training capture, and a single dashboard-ready structured log line."""
        if writeback and self._cache_enabled and not result.cached:
            await self.cache_engine.set(task, payload, result)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        await self._log_usage(context, task, result, tier=tier, escalated=escalated, latency_ms=latency_ms)
        if capture:
            await self._capture_result(context, task, payload, result, escalated=escalated)
        logger.info(
            "orchestrator_handled",
            task=task,
            engine_used=result.engine_used,
            engine=tier,
            cached=result.cached,
            confidence=result.confidence,
            latency_ms=latency_ms,
            cost_estimate_usd=self._tier_cost(tier, result),
        )
        return result

    async def _capture_result(
        self, context: dict, task: str, payload: dict, result: EngineResult, *, escalated: bool
    ) -> None:
        """Hand a served result to the training-capture hook (best-effort)."""
        if self._capture is None:
            return
        try:
            await self._capture.on_result(context, task, payload, result, escalated=escalated)
        except Exception as exc:  # noqa: BLE001 — capture must never break a request
            logger.warning("orchestrator_capture_failed", task=task, error=str(exc))

    async def _log_usage(
        self, context: dict, task: str, result: EngineResult, *,
        tier: str = "", escalated: bool = False, latency_ms: Optional[float] = None,
    ) -> None:
        """Persist an AiUsageLog row for a paid engine call (best-effort).

        Uses ``context["db"]`` when the caller supplies a session, otherwise an
        injected ``usage_session_factory``. With neither available, persistence
        is skipped so a missing DB never breaks a request (and unit tests never
        touch a real database).
        """
        session = context.get("db")
        cost = self._tier_cost(tier, result) if tier else result.cost_estimate_usd
        kwargs = dict(
            user_id=context.get("user_id"),
            task_type=task,
            engine_used=result.engine_used,
            engine_tier=tier,
            latency_ms=latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_estimate_usd=cost,
            escalated=escalated,
            confidence=result.confidence,
        )
        try:
            if session is not None:
                await record_usage(session, **kwargs)
            elif self._usage_session_factory is not None:
                async with self._usage_session_factory() as owned:
                    await record_usage(owned, **kwargs)
                    await owned.commit()
        except Exception as exc:  # noqa: BLE001 — cost logging must never break a request
            logger.warning("orchestrator_usage_log_failed", task=task, error=str(exc))


_default_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Process-wide Orchestrator singleton (engines are reusable & stateless).

    Lightweight entry point for call sites that route through the chain but do
    not need the gateway's knowledge grounding (e.g. agents that already build
    their own prompt/context).
    """
    global _default_orchestrator
    if _default_orchestrator is None:
        # Training capture is built from settings (None unless explicitly enabled).
        from app.training.capture import build_capture

        _default_orchestrator = Orchestrator(capture=build_capture())
    return _default_orchestrator
