"""EMBEDHUNT AI — LLM Model Selector & Routing Table.

Maps a semantic TaskType to a concrete Bedrock/Anthropic model. Model ids and
cost tiers are resolved from settings so the routing table is data-driven
rather than hardcoded. A per-task override channel supports deterministic
testing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.config.settings import settings


class TaskType(str, Enum):
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    MATCHING = "matching"
    MENTORING = "mentoring"
    PLANNING = "planning"
    INTERVIEW = "interview"
    CODING = "coding"
    SALARY = "salary"
    ROADMAP = "roadmap"
    COMPLEX_REASONING = "complex_reasoning"
    DOMAIN_CLASSIFICATION = "domain_classification"


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    max_tokens: int
    temperature: float
    cost_per_1k_input: float
    cost_per_1k_output: float
    context_window: int = 200_000


HAIKU = "haiku"
SONNET = "sonnet"
OPUS = "opus"

_DEFAULT_ROUTING: dict[TaskType, str] = {
    TaskType.EXTRACTION: HAIKU,
    TaskType.SUMMARIZATION: HAIKU,
    TaskType.MATCHING: SONNET,
    TaskType.MENTORING: SONNET,
    TaskType.PLANNING: SONNET,
    TaskType.INTERVIEW: SONNET,
    TaskType.CODING: SONNET,
    TaskType.SALARY: SONNET,
    TaskType.ROADMAP: SONNET,
    TaskType.COMPLEX_REASONING: OPUS,
    TaskType.DOMAIN_CLASSIFICATION: HAIKU,
}

# USD per 1,000 tokens (input, output) per tier.
_TIER_COST: dict[str, tuple[float, float]] = {
    HAIKU: (0.001, 0.005),
    SONNET: (0.003, 0.015),
    OPUS: (0.015, 0.075),
}
_TIER_MAX_TOKENS: dict[str, int] = {HAIKU: 2048, SONNET: 4096, OPUS: 8192}
_TIER_TEMPERATURE: dict[str, float] = {HAIKU: 0.2, SONNET: 0.4, OPUS: 0.5}
_TIER_CONTEXT_WINDOW: dict[str, int] = {HAIKU: 200_000, SONNET: 200_000, OPUS: 200_000}

# Task-level temperature overrides (deterministic tasks run colder).
_TASK_TEMPERATURE: dict[TaskType, float] = {
    TaskType.EXTRACTION: 0.0,
    TaskType.SUMMARIZATION: 0.1,
    TaskType.MATCHING: 0.2,
    TaskType.CODING: 0.2,
    TaskType.SALARY: 0.2,
    TaskType.DOMAIN_CLASSIFICATION: 0.0,
}

_OVERRIDES: dict[TaskType, str] = {}


def _routing_table() -> dict[TaskType, str]:
    table = dict(_DEFAULT_ROUTING)
    configured = getattr(settings, "LLM_TASK_ROUTING", None)
    if isinstance(configured, dict):
        for key, tier in configured.items():
            try:
                table[TaskType(key)] = tier
            except ValueError:
                continue
    return table


def _model_id_for_tier(tier: str) -> str:
    return {
        HAIKU: settings.LLM_HAIKU_MODEL,
        SONNET: settings.LLM_SONNET_MODEL,
        OPUS: settings.LLM_OPUS_MODEL,
    }.get(tier, settings.LLM_SONNET_MODEL)


def _tier_of_model(model_id: str) -> str:
    m = model_id.lower()
    if "haiku" in m:
        return HAIKU
    if "opus" in m:
        return OPUS
    return SONNET


def select_model(task: TaskType) -> ModelConfig:
    if task in _OVERRIDES:
        model_id = _OVERRIDES[task]
        tier = _tier_of_model(model_id)
    else:
        tier = _routing_table()[task]
        model_id = _model_id_for_tier(tier)
    cost_in, cost_out = _TIER_COST[tier]
    return ModelConfig(
        model_id=model_id,
        max_tokens=_TIER_MAX_TOKENS[tier],
        temperature=_TASK_TEMPERATURE.get(task, _TIER_TEMPERATURE[tier]),
        cost_per_1k_input=cost_in,
        cost_per_1k_output=cost_out,
        context_window=_TIER_CONTEXT_WINDOW[tier],
    )


def override_model(task: TaskType, model_id: str) -> None:
    _OVERRIDES[task] = model_id


def clear_overrides() -> None:
    _OVERRIDES.clear()
