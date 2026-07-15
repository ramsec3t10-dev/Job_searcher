"""EMBEDHUNT AI — Base Agent.

Every agent follows one fixed pipeline:

    Input -> ContextBuilder -> PromptTemplate -> AIRouter -> ResponseParser
          -> MemoryStore -> Output

BaseAgent owns the shared plumbing: the router, the Career Twin repository, the
long-term memory store, conversation history, the twin service and cost
tracking. Subclasses only wire task-specific context, prompt and response model.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.llm.conversation_manager import ConversationManager
from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.career_twin_service import CareerTwinService

logger = get_logger(__name__)


class BaseAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Phase 4: every agent routes AI through the orchestrator via _handle().
        # No agent holds a Bedrock/model-provider client anymore — providers are
        # fully behind the orchestrator (caching, gating, cost logging, routing).
        from app.orchestrator.router import get_orchestrator

        self.orchestrator = get_orchestrator()
        self.twin_repo = CareerTwinRepository(db)
        self.memory_repo = MemoryRepository(db)
        self.twin_service = CareerTwinService(db)
        self.conversation_manager = ConversationManager()
        # Set per public method call so _handle/_store_memory know the actor.
        self.user_id: str = ""

    async def _handle(self, task: str, system: str, user: str, max_tokens: int) -> str:
        """Route a single-turn request through the AI Orchestrator; return raw text.

        Drop-in replacement for :meth:`_call` (same raw-string contract, so all
        downstream ``parse_structured`` / ``_store_memory`` is unchanged) that
        goes through the full engine chain — rule → knowledge-graph → cache →
        open-model (gated) → Claude — instead of hitting Bedrock directly. Cost is
        logged to ``AiUsageLog`` with ``user_id`` by the orchestrator.
        """
        result = await self.orchestrator.handle(
            task,
            {"prompt": user, "system": system, "max_tokens": max_tokens},
            {"user_id": self.user_id, "db": self.db},
        )
        return result.text

    async def _store_memory(self, summary: str, memory_type: str, importance: int, tags: list) -> None:
        try:
            await self.memory_repo.store(
                self.user_id,
                memory_type,
                summary,
                importance_score=importance,
                tags=tags or [],
            )
        except Exception as exc:  # noqa: BLE001 — memory persistence is best-effort
            logger.warning("agent_store_memory_failed", error=str(exc))

    @staticmethod
    def _json(value: Any) -> str:
        """Compact JSON string for embedding structured context into a prompt."""
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)
