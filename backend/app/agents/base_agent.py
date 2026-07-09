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
from app.llm.cost_tracker import CostTracker
from app.llm.model_selector import TaskType
from app.llm.router import AIRouter
from app.repositories.career_twin_repository import CareerTwinRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.career_twin_service import CareerTwinService

logger = get_logger(__name__)


class BaseAgent:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.router = AIRouter()
        self.twin_repo = CareerTwinRepository(db)
        self.memory_repo = MemoryRepository(db, router=self.router)
        self.twin_service = CareerTwinService(db)
        self.conversation_manager = ConversationManager(router=self.router)
        self.cost_tracker = CostTracker()
        # Set per public method call so _call/_store_memory know the actor.
        self.user_id: str = ""

    async def _call(self, task: TaskType, system: str, user: str, max_tokens: int) -> str:
        """Route a single-turn request, track its cost, return raw content.

        ``user_id`` is intentionally NOT passed to the router (which would make
        it track usage too); cost tracking is done here exactly once.
        """
        response = await self.router.route(
            task,
            [{"role": "user", "content": user}],
            system,
            max_tokens,
        )
        try:
            await self.cost_tracker.track(self.user_id, response, db=self.db)
        except Exception as exc:  # noqa: BLE001 — cost tracking must never break a request
            logger.warning("agent_cost_track_failed", error=str(exc))
        return response.content

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
