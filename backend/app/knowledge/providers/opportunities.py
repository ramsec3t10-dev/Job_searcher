"""Opportunity/market providers: Skills, Companies, Jobs, Projects, Market, Salary."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.base import KnowledgeLayerProvider, LayerData
from app.knowledge.layers import KnowledgeLayer
from app.knowledge.providers._shared import load_twin
from app.models.discovered_job import DiscoveredJob
from app.models.recommendation import JobRecommendation
from app.models.user import User
from app.repositories.knowledge_graph_repository import KnowledgeGraphRepository


def _project_name(entry) -> str:
    if isinstance(entry, dict):
        return entry.get("name") or entry.get("title") or ""
    return str(entry)


class SkillsProvider(KnowledgeLayerProvider):
    """The candidate's skills + graph-derived gaps toward their target role."""

    layer = KnowledgeLayer.SKILLS
    source = "career_twins+knowledge_graph"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        if twin is None:
            return None
        known = [s.get("name", "") for s in (twin.skills or []) if s.get("name")]
        if not known:
            return None
        known_lower = {k.lower() for k in known}
        target_role = (twin.career_goals or {}).get("target_role") or ""

        missing: list[str] = []
        repo = KnowledgeGraphRepository(session)
        if target_role:
            role_reqs = await repo.get_role_requirements(target_role)
            missing = [n.name for n in role_reqs if n.name.lower() not in known_lower]
            if not role_reqs:
                # target_role may name a skill rather than a role — use prerequisites.
                prereqs = await repo.get_prerequisites(target_role)
                missing = [n.name for n in prereqs if n.name.lower() not in known_lower]

        facts = {
            "known_count": len(known),
            "known": known[:15],
            "target_role": target_role,
            "missing": missing,
        }
        gap = f"gaps: {', '.join(missing[:5])}" if missing else "no graph gaps identified"
        toward = f" toward {target_role}" if target_role else ""
        summary = f"{len(known)} skills{toward}; {gap}"
        return self._data(summary, facts)


class CompaniesProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.COMPANIES
    source = "career_twins+job_recommendations"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        dream = list(twin.dream_companies or []) if twin else []
        rows = (
            await session.execute(
                select(JobRecommendation.company_name, func.max(JobRecommendation.match_score))
                .where(JobRecommendation.user_id == user_id, JobRecommendation.is_dismissed == False)  # noqa: E712
                .group_by(JobRecommendation.company_name)
                .order_by(func.max(JobRecommendation.match_score).desc())
                .limit(3)
            )
        ).all()
        top_matched = [{"company": name, "score": int(score or 0)} for name, score in rows]
        if not dream and not top_matched:
            return None
        facts = {"dream_companies": dream, "top_matched": top_matched}
        parts = []
        if dream:
            parts.append(f"dream: {', '.join(dream[:4])}")
        if top_matched:
            parts.append("top matches: " + ", ".join(f"{m['company']} ({m['score']})" for m in top_matched))
        return self._data("; ".join(parts), facts)


class JobsProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.JOBS
    source = "applications+job_recommendations+discovered_jobs"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        from app.models.application import Application

        apps = (
            await session.execute(select(Application).where(Application.user_id == user_id))
        ).scalars().all()
        recs = (
            await session.execute(
                select(JobRecommendation)
                .where(JobRecommendation.user_id == user_id, JobRecommendation.is_dismissed == False)  # noqa: E712
                .order_by(JobRecommendation.match_score.desc())
                .limit(5)
            )
        ).scalars().all()
        if not apps and not recs:
            return None
        by_outcome: dict[str, int] = {}
        for app in apps:
            key = getattr(app.outcome, "value", str(app.outcome))
            by_outcome[key] = by_outcome.get(key, 0) + 1
        top_matches = [
            {"title": r.job_title, "company": r.company_name, "score": r.match_score} for r in recs[:3]
        ]
        active_market = (
            await session.execute(
                select(func.count()).select_from(DiscoveredJob).where(DiscoveredJob.is_active == True)  # noqa: E712
            )
        ).scalar_one()
        facts = {
            "applications": len(apps),
            "by_outcome": by_outcome,
            "recommendations": len(recs),
            "top_matches": top_matches,
            "active_market_jobs": int(active_market),
        }
        summary = (
            f"{len(apps)} applications, {len(recs)} live recommendations; "
            f"{int(active_market)} active roles in the market corpus"
        )
        return self._data(summary, facts)


class ProjectsProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.PROJECTS
    source = "career_twins.projects"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        if twin is None or not twin.projects:
            return None
        names = [n for n in (_project_name(p) for p in twin.projects) if n]
        facts = {"count": len(twin.projects), "names": names[:6]}
        listed = ", ".join(names[:4]) if names else f"{len(twin.projects)} projects"
        return self._data(f"{len(twin.projects)} portfolio projects: {listed}", facts)


class MarketProvider(KnowledgeLayerProvider):
    """Live embedded-job market snapshot from the discovered-jobs corpus."""

    layer = KnowledgeLayer.MARKET
    source = "discovered_jobs"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        active = (
            await session.execute(
                select(func.count()).select_from(DiscoveredJob).where(DiscoveredJob.is_active == True)  # noqa: E712
            )
        ).scalar_one()
        if not active:
            return None
        hirers = (
            await session.execute(
                select(DiscoveredJob.company, func.count())
                .where(DiscoveredJob.is_active == True)  # noqa: E712
                .group_by(DiscoveredJob.company)
                .order_by(func.count().desc())
                .limit(5)
            )
        ).all()
        sal_min, sal_max = (
            await session.execute(
                select(func.avg(DiscoveredJob.salary_min_lpa), func.avg(DiscoveredJob.salary_max_lpa))
                .where(DiscoveredJob.is_active == True)  # noqa: E712
            )
        ).one()
        top_hirers = [{"company": c, "openings": int(n)} for c, n in hirers]
        facts = {
            "active_jobs": int(active),
            "top_hirers": top_hirers,
            "salary_min_avg_lpa": round(float(sal_min), 1) if sal_min is not None else None,
            "salary_max_avg_lpa": round(float(sal_max), 1) if sal_max is not None else None,
        }
        band = ""
        if sal_min is not None and sal_max is not None:
            band = f"; typical {float(sal_min):.0f}–{float(sal_max):.0f} LPA"
        hirer_names = ", ".join(h["company"] for h in top_hirers[:3])
        summary = f"{int(active)} active embedded roles; top hirers: {hirer_names}{band}"
        return self._data(summary, facts)


class SalaryProvider(KnowledgeLayerProvider):
    layer = KnowledgeLayer.SALARY
    source = "career_twins+market"

    async def provide(self, user_id: str, session: AsyncSession, ctx) -> Optional[LayerData]:
        twin = await load_twin(ctx, session, user_id)
        if twin is not None:
            current, target, minimum = twin.current_salary_lpa, twin.target_salary_lpa, twin.min_salary_lpa
            market_value = twin.market_value_score
        else:
            user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if user is None:
                return None
            current, target, minimum, market_value = 0.0, user.target_salary_lpa, user.min_salary_lpa, 0
        if not any([current, target, minimum]):
            return None
        market = ctx.get(KnowledgeLayer.MARKET)
        market_range = None
        if market is not None:
            market_range = [market.facts.get("salary_min_avg_lpa"), market.facts.get("salary_max_avg_lpa")]
        facts = {
            "current_lpa": current,
            "target_lpa": target,
            "min_lpa": minimum,
            "market_value_score": market_value,
            "market_range_lpa": market_range,
        }
        summary = f"current {current:.0f} → target {target:.0f} LPA (floor {minimum:.0f}); market value {market_value}/100"
        return self._data(summary, facts)
