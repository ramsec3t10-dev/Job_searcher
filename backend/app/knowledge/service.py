"""EMBEDHUNT AI — Knowledge Architecture: service + orchestrator hand-off.

Convenience layer that (1) assembles a :class:`KnowledgeContext` for a user and
(2) turns it into the ``context`` dict the AI Orchestrator's ``handle`` expects.

The hand-off needs **no changes to the orchestrator or its engines**: the
knowledge brief is passed as ``context["system"]``, which both the Claude and
hosted-model engines already read as their system prompt — so every task the
orchestrator routes is automatically grounded in the user's knowledge stack.
The brief is PII-light by construction (built from provider summaries, which
avoid raw identifiers), keeping it safe to send to the third-party hosted model.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.assembler import KnowledgeAssembler
from app.knowledge.context import KnowledgeContext
from app.knowledge.layers import KnowledgeLayer


class KnowledgeService:
    def __init__(self, assembler: Optional[KnowledgeAssembler] = None):
        self.assembler = assembler or KnowledgeAssembler()

    async def build_context(
        self,
        user_id: str,
        session: AsyncSession,
        *,
        layers: Optional[list[KnowledgeLayer]] = None,
    ) -> KnowledgeContext:
        """Assemble the user's knowledge context (optionally a subset of layers)."""
        return await self.assembler.assemble(user_id, session, layers=layers)

    @staticmethod
    def orchestrator_context(
        knowledge: KnowledgeContext,
        *,
        session: Optional[AsyncSession] = None,
        include: Optional[list[KnowledgeLayer]] = None,
        extra: Optional[dict] = None,
    ) -> dict:
        """Build the ``context`` dict for ``Orchestrator.handle`` from a knowledge
        context.

        Injects the knowledge brief as ``system`` (consumed by the LLM engines),
        plus ``user_id`` (cost attribution) and ``db`` (cost logging) when a
        session is given. ``extra`` overrides/adds keys.
        """
        ctx: dict = {"user_id": knowledge.user_id}
        if session is not None:
            ctx["db"] = session
        preamble = knowledge.to_system_preamble(include)
        if preamble:
            ctx["system"] = preamble
        if extra:
            ctx.update(extra)
        return ctx
