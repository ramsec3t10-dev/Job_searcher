"""EMBEDHUNT AI — Per-task eval harness.

Scores a candidate model's answers against the *served reference* answers, per
task — the quality gate that decides whether a distilled model is ready to be
promoted into the orchestrator's routing.

Two scorers, matched to the task's output shape:
* **structured** (JSON tasks) — key/value agreement between reference & candidate.
* **freeform** — token-overlap (Jaccard) similarity.

Deterministic and dependency-free so it runs in CI. Real distillation would also
layer in human review and downstream outcome labels.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_interaction import AiInteraction
from app.orchestrator.hosted_model_engine import _strip_code_fence
from app.orchestrator.task_registry import is_structured_output

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class EvalReport:
    task: str
    n: int
    mean_score: float
    pass_rate: float
    threshold: float
    scores: list[float] = field(default_factory=list)

    def promotable(self) -> bool:
        """A simple promotion gate: strong average AND consistent pass rate."""
        return self.n > 0 and self.mean_score >= self.threshold and self.pass_rate >= 0.8


def _flatten(obj, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = str(obj).strip().lower()
    return out


def _try_json(text: str):
    try:
        return json.loads(_strip_code_fence(text or ""))
    except (ValueError, TypeError):
        return None


def structured_score(reference: str, candidate: str) -> float:
    """Key/value agreement between two JSON payloads (0–1)."""
    ref, cand = _try_json(reference), _try_json(candidate)
    if cand is None:
        return 0.0  # candidate didn't even produce valid JSON
    if ref is None:
        return 0.0
    r, c = _flatten(ref), _flatten(cand)
    keys = set(r) | set(c)
    if not keys:
        return 1.0
    matches = sum(1 for k in keys if r.get(k) == c.get(k))
    return matches / len(keys)


def freeform_score(reference: str, candidate: str) -> float:
    """Token-overlap (Jaccard) similarity between two texts (0–1)."""
    r = set(_TOKEN_RE.findall((reference or "").lower()))
    c = set(_TOKEN_RE.findall((candidate or "").lower()))
    if not r and not c:
        return 1.0
    if not r or not c:
        return 0.0
    return len(r & c) / len(r | c)


def score_example(task: str, reference: str, candidate: str) -> float:
    if is_structured_output(task):
        return structured_score(reference, candidate)
    return freeform_score(reference, candidate)


def evaluate(task: str, pairs: list[tuple[str, str]], *, threshold: float = 0.7) -> EvalReport:
    """Score ``(reference, candidate)`` text pairs for ``task``."""
    scores = [score_example(task, ref, cand) for ref, cand in pairs]
    n = len(scores)
    mean = sum(scores) / n if n else 0.0
    pass_rate = sum(1 for s in scores if s >= threshold) / n if n else 0.0
    return EvalReport(task, n, round(mean, 4), round(pass_rate, 4), threshold, [round(s, 4) for s in scores])


async def evaluate_shadow_capture(
    session: AsyncSession, task: str, *, threshold: float = 0.7, limit: Optional[int] = None
) -> EvalReport:
    """Offline eval of already-captured shadow candidates vs their served refs.

    Pulls ``shadow_candidate`` rows for ``task``, matches each to its parent
    ``served`` answer, and scores them — no model calls, pure offline. This is
    the day-to-day "how close is the candidate?" report.
    """
    stmt = select(AiInteraction).where(
        AiInteraction.task_type == task, AiInteraction.role == "shadow_candidate"
    ).order_by(AiInteraction.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    shadows = (await session.execute(stmt)).scalars().all()

    pairs: list[tuple[str, str]] = []
    for shadow in shadows:
        if not shadow.parent_id:
            continue
        parent = await session.get(AiInteraction, shadow.parent_id)
        if parent is None:
            continue
        pairs.append((parent.output, shadow.output))  # (reference, candidate)
    return evaluate(task, pairs, threshold=threshold)
