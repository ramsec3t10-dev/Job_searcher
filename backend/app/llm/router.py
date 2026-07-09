"""EMBEDHUNT AI — Unified AI Router.

The single entry point for all LLM traffic: selects a model for the task,
serves from cache when possible, invokes Bedrock, computes cost, tracks usage,
and returns a fully-populated AIResponse.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from app.config.logging import get_logger
from app.llm.bedrock_client import BedrockClient
from app.llm.cache import SemanticCache, ttl_for
from app.llm.cost_tracker import CostTracker
from app.llm.guardrails import sanitize_response, validate_request
from app.llm.model_selector import ModelConfig, TaskType, select_model

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.llm.prompts.base import PromptTemplate

logger = get_logger(__name__)


@dataclass
class AIResponse:
    content: str
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    cached: bool
    task_type: TaskType


class AIRouter:
    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        cache: Optional[SemanticCache] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.bedrock = bedrock_client or BedrockClient()
        self.cache = cache or SemanticCache()
        self.cost_tracker = cost_tracker or CostTracker()

    @staticmethod
    def _cost(config: ModelConfig, tokens_in: int, tokens_out: int) -> float:
        return round(
            (tokens_in / 1000) * config.cost_per_1k_input + (tokens_out / 1000) * config.cost_per_1k_output,
            6,
        )

    async def route(
        self,
        task: TaskType,
        messages: list,
        system: str = "",
        max_tokens: Optional[int] = None,
        *,
        user_id: Optional[str] = None,
        use_cache: bool = True,
        db: "Optional[AsyncSession]" = None,
    ) -> AIResponse:
        validate_request(task, messages)
        config = select_model(task)
        max_tokens = max_tokens or config.max_tokens
        user_content = messages[-1].get("content", "") if messages else ""
        cache_ttl = ttl_for(task)
        cacheable = use_cache and cache_ttl != 0
        key = SemanticCache.make_key(task, system, user_content)

        if cacheable:
            hit = await self.cache.get(key)
            if hit is not None:
                hit.cached = True
                logger.info("ai_cache_hit", task=task.value, model=hit.model_used)
                return hit

        start = time.perf_counter()
        result = await self.bedrock.invoke_model(
            config.model_id,
            messages,
            system=system or None,
            max_tokens=max_tokens,
            temperature=config.temperature,
        )
        latency = result.get("latency_ms") or round((time.perf_counter() - start) * 1000, 2)
        tokens_in = result["input_tokens"]
        tokens_out = result["output_tokens"]
        response = AIResponse(
            content=sanitize_response(result["content"]),
            model_used=config.model_id,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cost_usd=self._cost(config, tokens_in, tokens_out),
            latency_ms=latency,
            cached=False,
            task_type=task,
        )

        if cacheable:
            await self.cache.set(key, response, cache_ttl, user_id=user_id)
        if user_id:
            try:
                await self.cost_tracker.track(user_id, response, db=db)
            except Exception as exc:  # noqa: BLE001 — cost tracking must never break a request
                logger.warning("ai_cost_track_failed", error=str(exc))

        logger.info(
            "ai_route",
            task=task.value,
            model=config.model_id,
            cost_usd=response.cost_usd,
            latency_ms=latency,
        )
        return response

    async def run_prompt(
        self,
        template: "PromptTemplate",
        *,
        user_id: Optional[str] = None,
        use_cache: bool = True,
        db: "Optional[AsyncSession]" = None,
        **kwargs,
    ) -> AIResponse:
        """Render a PromptTemplate with kwargs and route it as a single-turn call."""
        user_message = template.render(**kwargs)
        return await self.route(
            template.task_type,
            [{"role": "user", "content": user_message}],
            system=template.system_prompt,
            max_tokens=template.max_tokens,
            user_id=user_id,
            use_cache=use_cache,
            db=db,
        )

