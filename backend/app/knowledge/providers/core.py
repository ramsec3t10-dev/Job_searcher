"""Core knowledge-layer providers: User, Career Twin, Memory, Knowledge Graph."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.base import KnowledgeLayerProvider, LayerData
from app.knowledge.layers import KnowledgeLayer
from app.knowledge.providers._shared import load_twin
from app.models.knowledge_graph import SkillNode
from app.models.memory import MemoryEntry
from app.models.profile import CandidateProfile
from app.models.user import User
from app.repositories.knowledge_graph_repository import KnowledgeGraphRepository


class UserProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.USER
    source = "user"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        profile = (
            await session.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
        ).scalar_one_or_none()
        if user is None and profile is None:
            return None
        role = getattr(getattr(user, "role", None), "value", "candidate") if user else "candidate"
        headline = getattr(profile, "headline", "") if profile else ""
        years = float(getattr(profile, "total_experience_years", 0.0) or 0.0) if profile else 0.0
        score = int(getattr(profile, "profile_score", 0) or 0) if profile else 0
        looking = bool(getattr(profile, "is_actively_looking", False)) if profile else False
        facts = {
            "role": role,
            "is_premium": bool(getattr(user, "is_premium", False)) if user else False,
            "headline": headline,
            "experience_years": round(years, 1),
            "profile_score": score,
            "actively_looking": looking,
        }
        status = "actively looking" if looking else "passive"
        summary = f"{headline or role} · {years:.0f}y experience · profile {score}/100 · {status}"
        return self._data(summary, facts)


class CareerTwinProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.CAREER_TWIN
    source = "career_twins"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        if twin is None:
            return None
        skills_count = len(twin.skills or [])
        facts = {
            "career_level": twin.career_level,
            "career_trajectory": twin.career_trajectory,
            "total_years_experience": twin.total_years_experience,
            "current_role": twin.current_role,
            "current_company": twin.current_company,
            "embedded_domain_score": twin.embedded_domain_score,
            "market_value_score": twin.market_value_score,
            "profile_completeness": twin.profile_completeness,
            "skills_count": skills_count,
            "version": twin.version,
        }
        role = twin.current_role or "engineer"
        at = f" at {twin.current_company}" if twin.current_company else ""
        summary = (
            f"{twin.career_level} {role}{at}, {twin.total_years_experience:.0f}y exp; "
            f"embedded score {twin.embedded_domain_score}/100, {skills_count} tracked skills "
            f"(twin v{twin.version})"
        )
        return self._data(summary, facts)


class MemoryProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.MEMORY
    source = "memory_entries"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        rows = (
            await session.execute(
                select(MemoryEntry)
                .where(MemoryEntry.user_id == user_id)
                .order_by(MemoryEntry.importance_score.desc(), MemoryEntry.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        if not rows:
            return None
        by_type: dict[str, int] = {}
        for row in rows:
            by_type[row.memory_type] = by_type.get(row.memory_type, 0) + 1
        top = [{"type": r.memory_type, "summary": r.summary[:160]} for r in rows[:3]]
        facts = {"recent_count": len(rows), "by_type": by_type, "top": top}
        headline = top[0]["summary"] if top else ""
        summary = f"{len(rows)} recent memories ({', '.join(by_type)}); latest: {headline}"
        return self._data(summary, facts)


class KnowledgeGraphProvider(KnowledgeLayerProvider):
    """The deterministic skill graph as a capability layer (user-agnostic)."""

    layer = KnowledgeLayer.KNOWLEDGE_GRAPH
    source = "knowledge_graph"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        node_count = (
            await session.execute(select(func.count()).select_from(SkillNode))
        ).scalar_one()
        if not node_count:
            return None
        roles = await KnowledgeGraphRepository(session).list_role_names()
        facts = {"skill_nodes": int(node_count), "roles": roles}
        summary = (
            f"Deterministic skill graph: {int(node_count)} skills, {len(roles)} role maps; "
            f"answers prerequisites & learning-paths with zero LLM"
        )
        return self._data(summary, facts)
