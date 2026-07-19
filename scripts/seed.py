"""EMBEDHUNT AI — Seed reference data (companies) into the database.

Idempotent: skips companies that already exist (by name). Safe to re-run.

Run from the backend/ directory:
    python ../scripts/seed.py
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.config.settings import settings  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.domain_taxonomy import JobDomain, Skill, SkillCategory  # noqa: E402
from app.domains.catalog import (  # noqa: E402
    DEFAULT_DOMAIN_CODE, EMBEDDED_CATEGORIES, flatten,
    domain_id, skill_category_id, skill_id,
)
from app.domains.skill_seed import DOMAIN_SKILL_SEED  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

# (name, tier, careers_url)
COMPANIES = [
    ("Qualcomm", "tier1_semiconductor", "https://careers.qualcomm.com"),
    ("NVIDIA", "tier1_semiconductor", "https://nvidia.com/careers"),
    ("NXP Semiconductors", "tier1_semiconductor", "https://careers.nxp.com"),
    ("Texas Instruments", "tier1_semiconductor", "https://careers.ti.com"),
    ("Infineon Technologies", "tier1_semiconductor", "https://infineon.com/careers"),
    ("AMD", "tier1_semiconductor", "https://jobs.amd.com"),
    ("STMicroelectronics", "tier1_semiconductor", "https://st.com/careers"),
    ("Bosch Global Software Technologies", "tier2_automotive", "https://bosch.com/careers"),
    ("KPIT Technologies", "tier2_automotive", "https://kpit.com/careers"),
    ("Continental", "tier2_automotive", "https://continental.com/careers"),
    ("Aptiv", "tier2_automotive", "https://aptiv.com/careers"),
    ("Harman International", "tier2_automotive", "https://harman.com/careers"),
    ("Tata Elxsi", "india_focused", "https://tataelxsi.com/careers"),
    ("L&T Technology Services", "india_focused", "https://ltts.com/careers"),
    ("Cisco Systems", "tier4_telecom", "https://jobs.cisco.com"),
    ("Siemens", "tier3_industrial", "https://jobs.siemens.com"),
]


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    created = 0
    domains_created = 0
    async with Session() as session:
        for name, tier, url in COMPANIES:
            exists = await session.scalar(select(Company).where(Company.name == name))
            if exists:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            session.add(Company(name=name, slug=slug, tier=tier, careers_url=url))
            created += 1

        # ── Job taxonomy (idempotent by id) — full plug-and-play hierarchy.
        # embedded_engineering ships with its migrated skill categories; other
        # nodes carry role keywords for classification (categories land later).
        tree = flatten()
        for d in tree:
            if await session.scalar(select(JobDomain).where(JobDomain.id == d.id)):
                continue
            session.add(JobDomain(id=d.id, code=d.code, name=d.name,
                                  description=d.description, is_active=True,
                                  parent_id=d.parent_id, level=d.level,
                                  keywords=d.keywords))
            domains_created += 1
            if d.code == DEFAULT_DOMAIN_CODE:
                for ccode, cname, weight in EMBEDDED_CATEGORIES:
                    session.add(SkillCategory(
                        id=skill_category_id(d.code, ccode), domain_id=d.id,
                        code=ccode, name=cname, weight=weight))

        # ── Real SkillCategory + Skill data for the first-wave domains ──────
        # (software_it, sales, finance). Other domains keep empty category sets.
        # TODO(phase-later): research + seed weights for the remaining domains
        # (healthcare, marketing, hr, mechanical, civil, ...). Do NOT fabricate.
        cats_created = skills_created = 0
        for dcode, categories in DOMAIN_SKILL_SEED.items():
            did = domain_id(dcode)
            for ccode, cname, weight, skills in categories:
                cid = skill_category_id(dcode, ccode)
                if not await session.scalar(select(SkillCategory).where(SkillCategory.id == cid)):
                    session.add(SkillCategory(id=cid, domain_id=did, code=ccode,
                                              name=cname, weight=weight))
                    cats_created += 1
                for sname, aliases in skills:
                    sid = skill_id(dcode, ccode, sname)
                    if not await session.scalar(select(Skill).where(Skill.id == sid)):
                        session.add(Skill(id=sid, category_id=cid, name=sname,
                                          aliases=list(aliases)))
                        skills_created += 1
        await session.commit()
    await engine.dispose()
    print(f"Seed complete. Added {created} new companies ({len(COMPANIES)} in catalog), "
          f"{domains_created} new domain nodes ({len(tree)} in catalog), "
          f"{cats_created} skill categories + {skills_created} skills "
          f"for {len(DOMAIN_SKILL_SEED)} domains.")


if __name__ == "__main__":
    asyncio.run(main())
