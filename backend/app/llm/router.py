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

# Rough token estimate (~4 chars/token) — good enough for budget/threshold gates.
def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


# Compress prompts larger than this (tokens) before hitting an expensive model.
_COMPRESSION_TOKEN_THRESHOLD = 3000
# Target size of a compressed prompt (tokens).
_COMPRESSION_TARGET_TOKENS = 1500
# Fraction of the context window above which oldest turns are summarised.
_CONTEXT_TRUNCATE_RATIO = 0.8
_EXPENSIVE_TIERS = ("sonnet", "opus")
# Tasks that benefit from embedding-similarity caching: free-text inputs where
# near-duplicates recur (a mentor question rephrased, the same job re-posted).
_SEMANTIC_CACHE_TASKS = frozenset({TaskType.MENTORING, TaskType.DOMAIN_CLASSIFICATION})


def _is_expensive(model_id: str) -> bool:
    return any(tier in (model_id or "").lower() for tier in _EXPENSIVE_TIERS)


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
        self._embedder = None

    def _embed(self, text: str) -> list[float]:
        """Local, cheap query embedding for the semantic cache (offline-capable)."""
        if self._embedder is None:
            from app.ai.embeddings import get_embedding_engine

            self._embedder = get_embedding_engine()
        return self._embedder.embed_text(text)

    async def compress_if_needed(self, prompt: str, config: ModelConfig) -> str:
        """Summarise oversized prompts before an expensive model call.

        Only fires for Sonnet/Opus on prompts above the token threshold; on any
        failure the original prompt is returned unchanged. Records the estimated
        token savings on the cost tracker.
        """
        original = estimate_tokens(prompt)
        if original <= _COMPRESSION_TOKEN_THRESHOLD or not _is_expensive(config.model_id):
            return prompt
        try:
            from app.llm.model_selector import HAIKU, _model_id_for_tier

            haiku_id = _model_id_for_tier(HAIKU)
            result = await self.bedrock.invoke_model(
                haiku_id,
                [{
                    "role": "user",
                    "content": (
                        f"Summarize this to {_COMPRESSION_TARGET_TOKENS} tokens preserving "
                        f"all technical detail:\n\n{prompt}"
                    ),
                }],
                max_tokens=_COMPRESSION_TARGET_TOKENS,
                temperature=0.1,
            )
        except Exception as exc:  # noqa: BLE001 — compression is best-effort
            logger.warning("prompt_compression_failed", error=str(exc))
            return prompt
        compressed = result.get("content") or prompt
        saved = original - estimate_tokens(compressed)
        if saved > 0:
            self.cost_tracker.record_compression(saved, config.cost_per_1k_output)
            logger.info("prompt_compressed", tokens_saved=saved)
        return compressed

    async def _truncate_context(self, messages: list, config: ModelConfig) -> list:
        """Summarise the oldest turns when history exceeds 80% of the window."""
        if len(messages) <= 2:
            return messages
        total = sum(estimate_tokens(m.get("content", "")) for m in messages)
        if total <= config.context_window * _CONTEXT_TRUNCATE_RATIO:
            return messages
        keep = messages[-2:]
        old = messages[:-2]
        joined = "\n".join(m.get("content", "") for m in old)
        try:
            from app.llm.model_selector import HAIKU, _model_id_for_tier

            result = await self.bedrock.invoke_model(
                _model_id_for_tier(HAIKU),
                [{"role": "user", "content": f"Summarize this conversation history concisely:\n\n{joined}"}],
                max_tokens=_COMPRESSION_TARGET_TOKENS,
                temperature=0.1,
            )
            summary = result.get("content") or joined
        except Exception as exc:  # noqa: BLE001 — truncation is best-effort
            logger.warning("context_truncation_failed", error=str(exc))
            return messages
        return [{"role": "user", "content": f"[Earlier conversation summary]\n{summary}"}, *keep]

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
        validate_request(task, messages, user_id=user_id)
        config = select_model(task)
        max_tokens = max_tokens or config.max_tokens
        user_content = messages[-1].get("content", "") if messages else ""
        cache_ttl = ttl_for(task)
        cacheable = use_cache and cache_ttl != 0
        semantic_enabled = use_cache and task in _SEMANTIC_CACHE_TASKS
        key = SemanticCache.make_key(task, system, user_content)

        if cacheable:
            hit = await self.cache.get(key)
            if hit is not None:
                hit.cached = True
                self.cost_tracker.record_cache_hit()
                logger.info("ai_cache_hit", task=task.value, model=hit.model_used)
                return hit

        query_embedding: list[float] = []
        if semantic_enabled:
            try:
                query_embedding = self._embed(user_content)
                similar = await self.cache.find_similar(query_embedding)
            except Exception as exc:  # noqa: BLE001 — semantic cache must never break a call
                logger.warning("semantic_cache_lookup_failed", error=str(exc))
                similar = None
            if similar is not None:
                similar.cached = True
                self.cost_tracker.record_cache_hit(similar.cost_usd)
                logger.info("ai_semantic_cache_hit", task=task.value)
                return similar

        messages = await self._truncate_context(messages, config)
        if messages:
            compressed = await self.compress_if_needed(messages[-1].get("content", ""), config)
            if compressed != messages[-1].get("content", ""):
                messages = [*messages[:-1], {**messages[-1], "content": compressed}]

        start = time.perf_counter()
        result = await self.bedrock.invoke_model(
            config.model_id,
            messages,
            system=system or None,
            max_tokens=max_tokens,
            temperature=config.temperature,
            task=task,
        )
        latency = result.get("latency_ms") or round((time.perf_counter() - start) * 1000, 2)
        tokens_in = result["input_tokens"]
        tokens_out = result["output_tokens"]
        response = AIResponse(
            content=sanitize_response(result["content"], user_id=user_id),
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
        if semantic_enabled and query_embedding:
            try:
                await self.cache.store_with_embedding(key, response, query_embedding)
            except Exception as exc:  # noqa: BLE001 — semantic cache write is best-effort
                logger.warning("semantic_cache_store_failed", error=str(exc))
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

