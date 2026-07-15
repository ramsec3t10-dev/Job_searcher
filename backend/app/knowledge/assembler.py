"""EMBEDHUNT AI — Knowledge Architecture: the assembler.

Walks the knowledge layers in dependency order and asks each registered provider
to contribute its :class:`LayerData`. Because it walks top-to-bottom, every
provider sees the already-assembled upstream context (e.g. Skills reads the
Career Twin; Salary reads Market). Providers are best-effort: a failure or
missing data is recorded on the context and never aborts assembly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logging import get_logger
from app.knowledge.base import KnowledgeLayerProvider
from app.knowledge.context import KnowledgeContext
from app.knowledge.layers import LAYER_SPECS, PLANNED, KnowledgeLayer, ordered_layers
from app.knowledge.providers import default_providers

logger = get_logger(__name__)


class KnowledgeAssembler:
    """Composes per-user :class:`KnowledgeContext` from the layer providers."""

    def __init__(self, providers: Optional[list[KnowledgeLayerProvider]] = None):
        provs = providers if providers is not None else default_providers()
        self._by_layer: dict[KnowledgeLayer, KnowledgeLayerProvider] = {p.layer: p for p in provs}

    async def assemble(
        self,
        user_id: str,
        session: AsyncSession,
        *,
        layers: Optional[list[KnowledgeLayer]] = None,
    ) -> KnowledgeContext:
        """Assemble the knowledge context for ``user_id``.

        Args:
            user_id: Whose knowledge to assemble.
            session: Async DB session used by all providers.
            layers: Optional subset to load (still visited in dependency order);
                ``None`` loads every layer.
        """
        ctx = KnowledgeContext(user_id=user_id)
        selected = {layer.value for layer in layers} if layers else None

        for layer in ordered_layers():
            if selected is not None and layer.value not in selected:
                continue
            provider = self._by_layer.get(layer)
            if provider is None:
                # No provider registered — declared-but-planned (e.g. Health).
                reason = "planned" if LAYER_SPECS[layer].status == PLANNED else "no_provider"
                ctx.mark_skipped(layer, reason)
                continue
            try:
                data = await provider.provide(user_id, session, ctx)
            except Exception as exc:  # noqa: BLE001 — one layer must never break the rest
                logger.warning("knowledge_layer_failed", layer=layer.value, error=str(exc))
                ctx.mark_skipped(layer, "error")
                continue
            if data is None:
                ctx.mark_skipped(layer, "no_data")
                continue
            ctx.set_layer(layer, data)

        ctx.assembled_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "knowledge_assembled",
            user_id=user_id,
            loaded=len(ctx.layers),
            skipped=len(ctx.skipped),
        )
        return ctx
