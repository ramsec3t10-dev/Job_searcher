"""EMBEDHUNT AI — Domain taxonomy repository."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_taxonomy import JobDomain, Skill, SkillCategory


class DomainRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, domain_id: str) -> Optional[JobDomain]:
        return await self.db.get(JobDomain, domain_id)

    async def get_by_code(self, code: str) -> Optional[JobDomain]:
        res = await self.db.execute(
            select(JobDomain).where(JobDomain.code == code))
        return res.scalar_one_or_none()

    async def list_domains(self, *, active_only: bool = False) -> list[JobDomain]:
        stmt = select(JobDomain).order_by(JobDomain.name)
        if active_only:
            stmt = stmt.where(JobDomain.is_active.is_(True))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_active_domains(self) -> list[JobDomain]:
        return await self.list_domains(active_only=True)

    async def get_skill_categories(self, domain_id: str) -> list[SkillCategory]:
        res = await self.db.execute(
            select(SkillCategory)
            .where(SkillCategory.domain_id == domain_id)
            .order_by(SkillCategory.weight.desc()))
        return list(res.scalars().all())

    async def get_skills(self, category_id: str) -> list[Skill]:
        res = await self.db.execute(
            select(Skill).where(Skill.category_id == category_id).order_by(Skill.name))
        return list(res.scalars().all())

    # ── CRUD ────────────────────────────────────────────────────────────
    async def create_domain(self, *, code: str, name: str,
                            description: str | None = None,
                            is_active: bool = True) -> JobDomain:
        domain = JobDomain(code=code, name=name, description=description,
                           is_active=is_active)
        self.db.add(domain)
        await self.db.flush()
        return domain

    async def create_category(self, *, domain_id: str, code: str, name: str,
                             weight: int = 10) -> SkillCategory:
        cat = SkillCategory(domain_id=domain_id, code=code, name=name, weight=weight)
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def create_skill(self, *, category_id: str, name: str,
                          aliases: list[str] | None = None) -> Skill:
        skill = Skill(category_id=category_id, name=name, aliases=aliases or [])
        self.db.add(skill)
        await self.db.flush()
        return skill

    async def set_domain_active(self, domain_id: str, is_active: bool) -> None:
        domain = await self.get(domain_id)
        if domain:
            domain.is_active = is_active
            await self.db.flush()
