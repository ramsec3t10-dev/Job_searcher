"""EMBEDHUNT AI — Knowledge Architecture package.

The *vertical* knowledge stack that grounds the *horizontal* AI Orchestrator:

    User → Career Twin → Memory → Knowledge Graph → Skills → Companies → Jobs
    → Projects → Learning → Interview → Market → Salary → Goals → Habits
    → Health (optional) → Professional Growth

Each layer is a :class:`~app.knowledge.base.KnowledgeLayerProvider` that reads
existing repositories/models and contributes one normalised
:class:`~app.knowledge.base.LayerData`. The :class:`~app.knowledge.assembler.KnowledgeAssembler`
walks the layers in dependency order into a single
:class:`~app.knowledge.context.KnowledgeContext`, and
:class:`~app.knowledge.service.KnowledgeService` turns that context into the
grounding the AI Orchestrator consumes. See ``app/knowledge/README.md``.
"""
from app.knowledge.assembler import KnowledgeAssembler
from app.knowledge.base import KnowledgeLayerProvider, LayerData
from app.knowledge.context import KnowledgeContext
from app.knowledge.layers import LAYER_SPECS, KnowledgeLayer, ordered_layers
from app.knowledge.service import KnowledgeService

__all__ = [
    "KnowledgeLayer",
    "LAYER_SPECS",
    "ordered_layers",
    "LayerData",
    "KnowledgeLayerProvider",
    "KnowledgeContext",
    "KnowledgeAssembler",
    "KnowledgeService",
]
