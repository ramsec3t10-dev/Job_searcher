"""EMBEDHUNT AI — Orchestrator Gateway.

The single front door every AI-needing service calls. It (1) assembles the
user's :class:`KnowledgeContext` (the vertical stack), (2) turns it into the
orchestrator ``context`` — grounding LLM engines via a PII-light ``system``
preamble — and (3) routes the task through the :class:`Orchestrator` fallthrough
chain (rule → knowledge-graph → cache → open model → Claude).

Services depend only on this gateway, so the whole architecture is swapped in at
one seam instead of at dozens of call sites.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.knowledge.service import KnowledgeService
from app.orchestrator.engine_base import EngineResult
from app.orchestrator.router import Orchestrator, get_orchestrator

logger = get_logger(__name__)


class OrchestratorGateway:
    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        knowledge: Optional[KnowledgeService] = None,
    ):
        # Share the singleton (with its training-capture wiring) by default.
        self.orchestrator = orchestrator or get_orchestrator()
        self.knowledge = knowledge or KnowledgeService()

    async def run(
        self,
        task: str,
        payload: dict,
        *,
        user_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        ground: bool = True,
        system: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> EngineResult:
        """Route ``task`` through the orchestrator, grounded in the user's knowledge.

        Args:
            task: Orchestrator task name (e.g. ``"company_summary"``, ``"mentor_chat"``).
            payload: Task inputs (JSON-serialisable).
            user_id: Whose knowledge to ground on / attribute cost to.
            session: DB session — enables knowledge assembly and cost logging.
            ground: Assemble + inject the user's knowledge brief as ``system``.
            system: A task/persona system prompt, prepended to the knowledge brief.
            extra: Extra context keys (override the computed ones).
        """
        context: dict = {}
        if user_id:
            context["user_id"] = user_id
        if session is not None:
            context["db"] = session

        preamble = ""
        if ground and user_id and session is not None:
            try:
                kctx = await self.knowledge.build_context(user_id, session)
                preamble = kctx.to_system_preamble()
            except Exception as exc:  # noqa: BLE001 — grounding is best-effort
                logger.warning("gateway_knowledge_failed", task=task, error=str(exc))

        combined_system = "\n\n".join(part for part in (system, preamble) if part)
        if combined_system:
            context["system"] = combined_system
        if extra:
            context.update(extra)

        return await self.orchestrator.handle(task, payload, context)


_default_gateway: Optional[OrchestratorGateway] = None


def get_gateway() -> OrchestratorGateway:
    """Process-wide gateway singleton (engines/providers are reusable & stateless)."""
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = OrchestratorGateway()
    return _default_gateway
