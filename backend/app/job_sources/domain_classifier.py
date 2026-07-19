"""EMBEDHUNT AI — Job posting → domain classifier (Phase 2).

Two tiers, cheapest first:

  1. **Rule tier** — matches the posting title/description against each
     top-level domain's discriminative role keywords (from the plug-and-play
     taxonomy). Zero cost, deterministic, resolves the large majority of
     postings (a "Data Scientist" or "Cabin Crew" title is unambiguous).
  2. **LLM tier (Haiku)** — only for genuinely ambiguous postings the rule tier
     can't place confidently. Routed through the existing AIRouter so it inherits
     guardrails → cache (exact + semantic) → compress → model-select, and cost
     tracking. Results are cached, and the same/similar postings recur, so the
     LLM is called rarely.

Classification is coarse (top-level domain) — the useful granularity for tagging
discovered jobs. The taxonomy's deeper levels remain available for later phases.
The classifier reads the catalog directly (same source of truth as the DB), so
it needs no database and is fully unit-testable without network or DB.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from app.config.logging import get_logger
from app.config.settings import settings
from app.domains.catalog import FlatDomain, domain_id, top_level_domains
from app.llm.model_selector import TaskType

logger = get_logger(__name__)

# Rule-tier confidence: a multi-word role phrase in the title is near-certain;
# a single keyword only in the body is weak.
_TITLE_PHRASE = 0.95
_TITLE_WORD = 0.70
_BODY_PHRASE = 0.55
_BODY_WORD = 0.35
_DEFAULT_MIN_RULE_CONFIDENCE = 0.6


@dataclass
class ClassificationResult:
    code: str
    confidence: float
    method: str          # "rule" | "llm" | "rule_low" | "fallback"

    @property
    def domain_id(self) -> str:
        return domain_id(self.code)


class DomainClassifier:
    def __init__(self, router=None, *,
                 min_rule_confidence: float = _DEFAULT_MIN_RULE_CONFIDENCE) -> None:
        self.router = router
        self.min_rule_confidence = min_rule_confidence
        self._domains: list[FlatDomain] = top_level_domains()
        self._codes = {d.code for d in self._domains}

    # ── Rule tier ────────────────────────────────────────────────────────
    @staticmethod
    def _score(domain: FlatDomain, title_l: str, hay_l: str) -> float:
        best = 0.0
        for kw in domain.keywords:
            if not kw:
                continue
            phrase = " " in kw
            if kw in title_l:
                best = max(best, _TITLE_PHRASE if phrase else _TITLE_WORD)
            elif kw in hay_l:
                best = max(best, _BODY_PHRASE if phrase else _BODY_WORD)
        return best

    def score_all(self, title: str, description: str) -> dict[str, float]:
        """Rule-tier score for every top-level domain (0 excluded). Shared by the
        job classifier and the resume classifier's primary/secondary selection."""
        title_l = (title or "").lower()
        hay_l = f"{title_l} {(description or '').lower()}"
        scores: dict[str, float] = {}
        for d in self._domains:
            if d.code == "other":
                continue
            s = self._score(d, title_l, hay_l)
            if s > 0.0:
                scores[d.code] = round(s, 2)
        return scores

    def classify_rule(self, title: str, description: str) -> Optional[ClassificationResult]:
        scores = self.score_all(title, description)
        if not scores:
            return None
        best_code = max(scores, key=scores.get)
        return ClassificationResult(best_code, scores[best_code], "rule")

    # ── LLM tier ─────────────────────────────────────────────────────────
    async def _classify_llm(self, title: str, description: str, *,
                            user_id: Optional[str], db) -> Optional[ClassificationResult]:
        catalog = "\n".join(f"- {d.code}: {d.name}" for d in self._domains)
        system = (
            "You classify a job posting into exactly one domain code from the "
            "provided list. Respond with ONLY a compact JSON object: "
            '{"code": "<domain_code>", "confidence": <0.0-1.0>}. '
            "Use \"other\" only if nothing fits."
        )
        user = (
            f"Domains:\n{catalog}\n\n"
            f"Job title: {title}\n"
            f"Description (truncated): {(description or '')[:1200]}\n\n"
            "Return the single best domain code as JSON."
        )
        try:
            resp = await self.router.route(
                TaskType.DOMAIN_CLASSIFICATION,
                [{"role": "user", "content": user}],
                system=system, user_id=user_id, db=db,
            )
            data = _parse_json(resp.content)
            code = str(data.get("code", "")).strip()
            conf = float(data.get("confidence", 0.5) or 0.5)
            if code in self._codes:
                return ClassificationResult(code, round(min(max(conf, 0.0), 1.0), 2), "llm")
            logger.warning("domain_classifier_unknown_code", code=code)
        except Exception as exc:  # noqa: BLE001 — classification must never break ingestion
            logger.warning("domain_classifier_llm_failed", error=str(exc))
        return None

    # ── Public API ───────────────────────────────────────────────────────
    async def classify(self, title: str, description: str = "", *,
                       user_id: Optional[str] = None, db=None) -> ClassificationResult:
        rule = self.classify_rule(title, description)
        if rule and rule.confidence >= self.min_rule_confidence:
            return rule
        if self.router is not None and settings.LLM_ENRICHMENT_ENABLED:
            llm = await self._classify_llm(title, description, user_id=user_id, db=db)
            if llm is not None:
                return llm
        if rule is not None:
            return ClassificationResult(rule.code, rule.confidence, "rule_low")
        return ClassificationResult("other", 0.0, "fallback")


def _parse_json(text: str) -> dict:
    """Tolerant JSON extraction from an LLM reply (handles ``` fences / prose)."""
    text = (text or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {}
