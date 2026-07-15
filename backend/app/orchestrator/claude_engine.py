"""EMBEDHUNT AI — Claude inference engine.

Adapts the existing :class:`app.llm.router.AIRouter` (AWS Bedrock / Anthropic
Claude) to the Orchestrator's :class:`InferenceEngine` interface. No new auth or
client is introduced here: the engine reuses AIRouter, which already owns the
Bedrock credentials, task→model selection, guardrails, cost tracking and its own
response cache. This is the terminal engine — it handles anything the earlier
engines fall through on.
"""
from __future__ import annotations

import json
from typing import Optional

from app.config.logging import get_logger
from app.llm.model_selector import TaskType
from app.llm.router import AIRouter
from app.orchestrator.engine_base import EngineResult, InferenceEngine

logger = get_logger(__name__)

# Orchestrator task names that map onto a specific LLM TaskType. A task string
# that is already a TaskType value resolves directly; anything unknown uses
# _DEFAULT_TASK_TYPE (a general single-turn call).
_TASK_TYPE_ALIASES: dict[str, TaskType] = {
    "daily_brief": TaskType.SUMMARIZATION,
    "brief": TaskType.SUMMARIZATION,
    "summary": TaskType.SUMMARIZATION,
    "match": TaskType.MATCHING,
    "mentor": TaskType.MENTORING,
    "plan": TaskType.PLANNING,
    # Orchestrator task names → LLM tier (used when a task escalates to Claude).
    "mentor_chat": TaskType.MENTORING,
    "mentor_daily_brief": TaskType.MENTORING,
    "match_explanation": TaskType.MATCHING,
    "negotiation_advice": TaskType.MENTORING,
    "interview_evaluation": TaskType.INTERVIEW,
    "interview_questions": TaskType.INTERVIEW,
    "lesson_generation": TaskType.PLANNING,
    "flashcard_generation": TaskType.EXTRACTION,
    "gap_analysis_explanation": TaskType.MATCHING,
    "resume_rewrite": TaskType.PLANNING,   # high-stakes writing → Sonnet tier
    "resume_score": TaskType.MATCHING,
    "company_summary": TaskType.SUMMARIZATION,
    "job_description_extraction": TaskType.EXTRACTION,
    "skill_extraction": TaskType.EXTRACTION,
    "resume_parsing": TaskType.EXTRACTION,
    "roadmap_draft": TaskType.ROADMAP,
    "coding_review_explanation": TaskType.CODING,
    "coding_challenge": TaskType.CODING,
    "salary_estimate": TaskType.SALARY,
    "memory_summarize": TaskType.SUMMARIZATION,
    "conversation_summarize": TaskType.SUMMARIZATION,
}
_DEFAULT_TASK_TYPE = TaskType.SUMMARIZATION


class ClaudeEngine(InferenceEngine):
    """Terminal engine: routes anything the earlier engines skip to Claude."""

    def __init__(self, router: Optional[AIRouter] = None):
        self.router = router or AIRouter()

    @staticmethod
    def _task_type_for(task: str) -> TaskType:
        """Resolve an orchestrator task string to an LLM :class:`TaskType`."""
        try:
            return TaskType(task)
        except ValueError:
            return _TASK_TYPE_ALIASES.get(task, _DEFAULT_TASK_TYPE)

    @staticmethod
    def _messages_for(payload: dict) -> list[dict]:
        """Build a Bedrock message list from the payload.

        Accepts either a ready ``messages`` list or a single ``prompt``/``input``
        string; as a last resort the whole payload is serialised so a call still
        runs rather than erroring.
        """
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            return messages
        prompt = payload.get("prompt") or payload.get("input")
        if not prompt:
            prompt = json.dumps(payload, sort_keys=True, default=str)
        return [{"role": "user", "content": prompt}]

    async def run(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        """Route ``task``/``payload`` through AIRouter and adapt the response."""
        context = context or {}
        task_type = self._task_type_for(task)
        system = payload.get("system") or context.get("system") or ""
        messages = self._messages_for(payload)

        response = await self.router.route(
            task_type,
            messages,
            system=system,
            max_tokens=payload.get("max_tokens"),  # honor the caller's token budget
            user_id=context.get("user_id"),
            use_cache=context.get("use_cache", True),
        )
        logger.info(
            "orchestrator_claude_engine",
            task=task,
            model=response.model_used,
            cached=response.cached,
        )
        return EngineResult(
            text=response.content,
            engine_used=f"claude:{response.model_used}",
            confidence=None,
            cached=response.cached,
            cost_estimate_usd=response.cost_usd,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
        )
