"""EMBEDHUNT AI — Knowledge Architecture: provider interface.

Every knowledge layer is produced by a :class:`KnowledgeLayerProvider`. A
provider reads existing repositories/models (and, if useful, the already-loaded
upstream layers on the passed-in context) and returns a single normalised
:class:`LayerData`, or ``None`` when the user has no data for that layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.layers import KnowledgeLayer

if TYPE_CHECKING:
    from app.knowledge.context import KnowledgeContext


class LayerData(BaseModel):
    """Normalised output of one knowledge layer.

    ``summary`` is a compact, deterministic, PII-light digest (safe to inject
    into an LLM prompt); ``facts`` carries the structured detail for programmatic
    consumers.
    """

    layer: str
    summary: str = ""
    facts: dict[str, Any] = Field(default_factory=dict)
    source: str = ""
    confidence: float = 1.0


class KnowledgeLayerProvider(ABC):
    """Produces the :class:`LayerData` for one :class:`KnowledgeLayer`."""

    layer: ClassVar[KnowledgeLayer]
    source: ClassVar[str] = ""

    @abstractmethod
    async def provide(
        self, user_id: str, session: AsyncSession, ctx: "KnowledgeContext"
    ) -> Optional[LayerData]:
        """Return this layer's data for ``user_id``, or ``None`` if none exists."""
        ...

    def _data(
        self, summary: str, facts: Optional[dict] = None, confidence: float = 1.0
    ) -> LayerData:
        """Helper to build a :class:`LayerData` tagged with this layer/source."""
        return LayerData(
            layer=self.layer.value,
            summary=summary,
            facts=facts or {},
            source=self.source or self.layer.value,
            confidence=confidence,
        )
