"""Shadow candidate-model engine (log-only).

Builds an OpenAI-compatible engine pointed at your *candidate* model (your own
fine-tune, served on vLLM/Ollama). It is used only to generate answers that are
**logged for evaluation, never served** — so you can measure a distilled model
against the incumbent on real traffic with zero user risk.
"""
from __future__ import annotations

from app.config.settings import settings
from app.orchestrator.hosted_model_engine import HostedModelEngine


def build_shadow_engine() -> HostedModelEngine:
    """Construct the shadow engine from ``SHADOW_MODEL_*`` settings.

    ``provider="shadow"`` needs no API key (self-hosted) and forces this single
    model for every task via :meth:`HostedModelEngine.generate` (bypassing the
    production fleet routing and the allowlist gate).
    """
    return HostedModelEngine(
        provider=settings.SHADOW_MODEL_PROVIDER,
        base_url=settings.SHADOW_MODEL_BASE_URL,
        api_key=settings.SHADOW_MODEL_API_KEY,
        model=settings.SHADOW_MODEL_NAME,
    )
