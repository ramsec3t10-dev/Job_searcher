"""EMBEDHUNT AI — Job domains API (Phase 6).

Lists the taxonomy's domains for the mobile onboarding domain picker. Backed by
the Phase-1 DomainRepository (active JobDomain rows). Top-level domains only by
default (the pickable set); pass ?all=true for the full hierarchy.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.repositories.domain_repository import DomainRepository

router = APIRouter(prefix="/domains", tags=["Domains"])


@router.get("", summary="List active job domains (top-level by default)")
async def list_domains(all: bool = False, user_id: str = Depends(get_current_user_id),
                       db: AsyncSession = Depends(get_db)):
    domains = await DomainRepository(db).list_active_domains()
    if not all:
        domains = [d for d in domains if d.level == 0]
    return {
        "domains": [
            {"code": d.code, "name": d.name, "description": d.description, "level": d.level}
            for d in sorted(domains, key=lambda x: x.name)
        ]
    }
