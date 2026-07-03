"""EMBEDHUNT AI — Career Mentor Engine (Module 15).

A conversational mentor grounded in the candidate's CareerTwin. When an
Anthropic API key is configured it uses Claude; otherwise it degrades
gracefully to a deterministic, context-aware advisor so the feature is always
available (including offline / no-key deployments).
"""
from __future__ import annotations

import json

import httpx

from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_SYSTEM_PROMPT = (
    "You are EmbedHunt's AI Career Mentor for embedded-systems and firmware "
    "engineers. Be concise, specific and encouraging. Ground every answer in "
    "the candidate context provided. Prefer concrete next actions (skills to "
    "learn, companies to target, interview topics) over generic advice."
)


class CareerMentorEngine:
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.MENTOR_MODEL

    @property
    def uses_llm(self) -> bool:
        return bool(self.api_key)

    async def answer(self, message: str, context: dict, history: list[dict] | None = None) -> dict:
        if self.uses_llm:
            try:
                reply = await self._ask_claude(message, context, history or [])
                return {"reply": reply, "source": "claude", "model": self.model}
            except Exception as exc:  # noqa: BLE001 — always fall back, never 500
                logger.warning("mentor_llm_failed", error=str(exc))
        return {"reply": self._fallback(message, context), "source": "rule_based", "model": None}

    # ── LLM path ──────────────────────────────────────────────────────────
    async def _ask_claude(self, message: str, context: dict, history: list[dict]) -> str:
        messages = [
            {"role": h.get("role", "user"), "content": h.get("content", "")}
            for h in history
            if h.get("content")
        ]
        messages.append({
            "role": "user",
            "content": f"Candidate context:\n{json.dumps(context, indent=2)}\n\nQuestion: {message}",
        })
        payload = {
            "model": self.model,
            "max_tokens": settings.MENTOR_MAX_TOKENS,
            "system": _SYSTEM_PROMPT,
            "messages": messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_ANTHROPIC_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()

    # ── Deterministic fallback ────────────────────────────────────────────
    def _fallback(self, message: str, ctx: dict) -> str:
        q = message.lower()
        name = ctx.get("full_name") or "there"
        weaknesses = ctx.get("known_weaknesses") or []
        top_skills = ctx.get("top_skills") or []
        readiness = ctx.get("interview_readiness_score", 0)
        market = ctx.get("market_value_score", 0)
        dream = ctx.get("dream_companies") or []

        if any(k in q for k in ("salary", "pay", "compensation", "underpaid", "raise")):
            return (
                f"On compensation: your market-value score is {market}/100. "
                "Open the Salary Intelligence tab for a precise LPA range and a "
                "negotiation brief. High-leverage skills like AUTOSAR, ISO 26262 "
                "and embedded Linux visibly raise your band."
            )
        if any(k in q for k in ("interview", "prepare", "ready", "mock")):
            focus = ", ".join(weaknesses[:3]) if weaknesses else "your weakest confidence skills"
            return (
                f"Your interview readiness is {readiness}/100. Prioritise {focus}. "
                "Run a Mock Interview session and record the outcome so your "
                "Career Twin adapts your roadmap automatically."
            )
        if any(k in q for k in ("learn", "skill", "improve", "roadmap", "gap")):
            gap = ", ".join(weaknesses[:3]) if weaknesses else "high-premium embedded skills"
            return (
                f"To grow fastest, close these gaps first: {gap}. Use the "
                "Simulation tab to see exactly how many new jobs each skill "
                "unlocks before you commit study time."
            )
        if any(k in q for k in ("company", "apply", "target", "job")):
            targets = ", ".join(dream[:3]) if dream else "Tier-1 semiconductor and automotive firms"
            return (
                f"Focus your applications on {targets}. The Jobs tab already "
                "ranks live roles by match score — start with your strong "
                "matches and let auto-apply queue the best ones."
            )
        strengths = ", ".join(top_skills[:3]) if top_skills else "your core embedded skills"
        return (
            f"Hi {name} — your strengths are {strengths}. Tell me whether you "
            "want help with skills, interviews, salary, or target companies and "
            "I'll give you a focused plan."
        )
