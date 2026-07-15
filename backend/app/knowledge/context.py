"""EMBEDHUNT AI — Knowledge Architecture: the assembled context.

:class:`KnowledgeContext` is the single object the vertical stack produces and
the AI Orchestrator consumes. It holds one :class:`LayerData` slot per loaded
layer, records why any layer was skipped, and renders a compact, PII-light
"brief" / system preamble for grounding LLM calls.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

from app.knowledge.base import LayerData
from app.knowledge.layers import LAYER_SPECS, KnowledgeLayer, ordered_layers


class KnowledgeContext(BaseModel):
    user_id: str
    # layer value → LayerData for every successfully-loaded layer.
    layers: dict[str, LayerData] = Field(default_factory=dict)
    # layer value → reason ("planned" | "no_data" | "error") for skipped layers.
    skipped: dict[str, str] = Field(default_factory=dict)
    assembled_at: Optional[str] = None

    # Runtime-only scratch space so providers can hand ORM objects downstream
    # (e.g. the Career Twin) without re-querying. Never serialised.
    _stash: dict = PrivateAttr(default_factory=dict)

    # ── mutation ────────────────────────────────────────────────────────────
    def set_layer(self, layer: KnowledgeLayer, data: LayerData) -> None:
        self.layers[layer.value] = data

    def mark_skipped(self, layer: KnowledgeLayer, reason: str) -> None:
        self.skipped[layer.value] = reason

    def stash(self, key: str, value) -> None:
        self._stash[key] = value

    def stashed(self, key: str, default=None):
        return self._stash.get(key, default)

    # ── access ──────────────────────────────────────────────────────────────
    def get(self, layer: KnowledgeLayer) -> Optional[LayerData]:
        return self.layers.get(layer.value)

    @property
    def loaded(self) -> list[str]:
        """Loaded layer names in dependency order."""
        return [layer.value for layer in ordered_layers() if layer.value in self.layers]

    # Typed accessors — convenience for callers that want one specific layer.
    @property
    def user(self) -> Optional[LayerData]: return self.layers.get("user")
    @property
    def career_twin(self) -> Optional[LayerData]: return self.layers.get("career_twin")
    @property
    def memory(self) -> Optional[LayerData]: return self.layers.get("memory")
    @property
    def knowledge_graph(self) -> Optional[LayerData]: return self.layers.get("knowledge_graph")
    @property
    def skills(self) -> Optional[LayerData]: return self.layers.get("skills")
    @property
    def companies(self) -> Optional[LayerData]: return self.layers.get("companies")
    @property
    def jobs(self) -> Optional[LayerData]: return self.layers.get("jobs")
    @property
    def projects(self) -> Optional[LayerData]: return self.layers.get("projects")
    @property
    def learning(self) -> Optional[LayerData]: return self.layers.get("learning")
    @property
    def interview(self) -> Optional[LayerData]: return self.layers.get("interview")
    @property
    def market(self) -> Optional[LayerData]: return self.layers.get("market")
    @property
    def salary(self) -> Optional[LayerData]: return self.layers.get("salary")
    @property
    def goals(self) -> Optional[LayerData]: return self.layers.get("goals")
    @property
    def habits(self) -> Optional[LayerData]: return self.layers.get("habits")
    @property
    def health(self) -> Optional[LayerData]: return self.layers.get("health")
    @property
    def professional_growth(self) -> Optional[LayerData]: return self.layers.get("professional_growth")

    # ── rendering ───────────────────────────────────────────────────────────
    def to_brief(self, include: Optional[list[KnowledgeLayer]] = None) -> str:
        """Compact one-line-per-layer digest, in dependency order."""
        include_values = {layer.value for layer in include} if include else None
        lines: list[str] = []
        for layer in ordered_layers():
            data = self.layers.get(layer.value)
            if data is None or not data.summary:
                continue
            if include_values is not None and layer.value not in include_values:
                continue
            lines.append(f"- {LAYER_SPECS[layer].title}: {data.summary}")
        return "\n".join(lines)

    def to_system_preamble(self, include: Optional[list[KnowledgeLayer]] = None) -> str:
        """Grounding preamble for LLM calls. PII-light by construction (built from
        provider summaries, which avoid raw identifiers)."""
        body = self.to_brief(include)
        if not body:
            return ""
        return (
            "You have the following grounded, up-to-date context about this "
            "candidate (derived deterministically from their Career Twin and "
            "platform data — treat it as authoritative):\n" + body
        )

    def to_facts(self) -> dict[str, dict]:
        """Structured facts per loaded layer, for programmatic consumers."""
        return {name: data.facts for name, data in self.layers.items()}
