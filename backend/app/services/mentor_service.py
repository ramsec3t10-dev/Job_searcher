"""EMBEDHUNT AI — Career Mentor Service (Module 15).

Routes mentor chat through the AI Orchestrator (``mentor_chat`` is a Claude-tier
task) via the :class:`OrchestratorGateway`, grounded in the candidate's
knowledge stack. If the orchestrator path yields nothing (e.g. no LLM
configured), it degrades to the deterministic CareerTwin-based advisor so the
feature is always available.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.mentor.career_mentor import _SYSTEM_PROMPT, CareerMentorEngine
from app.orchestrator.gateway import OrchestratorGateway, get_gateway
from app.services.career_twin_service import CareerTwinService

logger = get_logger(__name__)


class MentorService:
    def __init__(self, db: AsyncSession, gateway: OrchestratorGateway | None = None):
        self.db = db
        self.twin_svc = CareerTwinService(db)
        self.engine = CareerMentorEngine()  # retained for the deterministic fallback
        self.gateway = gateway or get_gateway()

    async def chat(self, user_id: str, message: str, history: list[dict] | None = None) -> dict:
        # Primary path: orchestrator (rule → KG → cache → open model → Claude),
        # grounded in the user's knowledge context. mentor_chat is Claude-only.
        try:
            result = await self.gateway.run(
                "mentor_chat",
                {"prompt": message, "messages": history or []},
                user_id=user_id,
                session=self.db,
                system=_SYSTEM_PROMPT,
            )
            reply = (result.text or "").strip()
            if reply:
                logger.info("mentor_chat", user_id=user_id, engine=result.engine_used)
                return {"reply": reply, "source": result.engine_used, "model": result.engine_used}
        except Exception as exc:  # noqa: BLE001 — always fall back, never 500
            logger.warning("mentor_orchestrator_failed", user_id=user_id, error=str(exc))

        # Deterministic fallback grounded in the CareerTwin.
        context = await self._build_context(user_id)
        reply = self.engine._fallback(message, context)
        logger.info("mentor_chat", user_id=user_id, source="rule_based")
        return {"reply": reply, "source": "rule_based", "model": None}

    async def _build_context(self, user_id: str) -> dict:
        try:
            summary = await self.twin_svc.get_twin_summary(user_id)
            twin = await self.twin_svc.get_twin(user_id)
        except Exception:  # noqa: BLE001 — mentor works even without a twin
            return {"full_name": "", "note": "Career Twin not initialized."}
        return {
            "full_name": summary.get("full_name"),
            "current_role": summary.get("current_role"),
            "career_level": summary.get("career_level"),
            "total_years_experience": summary.get("total_years_experience"),
            "top_skills": summary.get("top_skills"),
            "interview_readiness_score": summary.get("interview_readiness_score"),
            "market_value_score": summary.get("market_value_score"),
            "embedded_domain_score": summary.get("embedded_domain_score"),
            "dream_companies": summary.get("dream_companies"),
            "known_weaknesses": list(twin.known_weaknesses or []),
            "strengths": list(twin.strengths or []),
        }
