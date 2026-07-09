"""EMBEDHUNT AI — Token budgeting utilities.

Lightweight, dependency-free token estimation and context assembly used to
keep prompts within a model's context budget without a tokenizer dependency.
"""
from __future__ import annotations


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def build_context_within_budget(components: list[tuple[str, str, int]], budget: int) -> str:
    """Assemble context from (name, content, priority) parts, dropping the
    lowest-priority parts first when the token budget would be exceeded."""
    ordered = sorted(components, key=lambda c: c[2], reverse=True)
    chosen: list[tuple[str, str, int]] = []
    used = 0
    for name, content, priority in ordered:
        cost = estimate_tokens(name) + estimate_tokens(content) + 4
        if used + cost <= budget:
            chosen.append((name, content, priority))
            used += cost
    return "\n\n".join(f"## {name}\n{content}" for name, content, _ in chosen)


def compress_text(text: str, target_tokens: int) -> str:
    if estimate_tokens(text) <= target_tokens:
        return text
    max_chars = max(1, target_tokens * 4)
    truncated = text[:max_chars]
    for separator in (". ", "! ", "? ", "\n"):
        idx = truncated.rfind(separator)
        if idx > max_chars * 0.5:
            return truncated[:idx + 1].strip()
    return truncated.strip()
