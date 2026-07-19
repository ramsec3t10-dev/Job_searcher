"""EMBEDHUNT AI — Profile API"""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.auth.permissions import get_current_user_id
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Candidate Profile"])

@router.get("/", summary="Get full candidate profile built from primary resume")
async def get_profile(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    return await ProfileService(db).get_profile_dict(user_id)


@router.get("/progress", summary="Server-side sync: pull learning progress (lessons, badges, alias)")
async def get_progress(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.memory import MemoryEntry
    row = (await db.execute(
        select(MemoryEntry).where(MemoryEntry.user_id == user_id,
                                  MemoryEntry.memory_type == "app_progress")
        .order_by(MemoryEntry.created_at.desc()).limit(1))).scalar_one_or_none()
    import json as _json
    return _json.loads(row.content) if row and row.content else {}


@router.put("/progress", summary="Server-side sync: push learning progress")
async def put_progress(payload: dict = Body(...), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.memory import MemoryEntry
    import json as _json
    row = (await db.execute(
        select(MemoryEntry).where(MemoryEntry.user_id == user_id,
                                  MemoryEntry.memory_type == "app_progress")
        .limit(1))).scalar_one_or_none()
    if row is None:
        row = MemoryEntry(user_id=user_id, memory_type="app_progress", content="{}")
        db.add(row)
    row.content = _json.dumps(payload)
    await db.flush()
    return {"synced": True}


@router.get("/domains", summary="Get the candidate's declared target domain(s)")
async def get_target_domains(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.domains.catalog import code_for_domain_id, top_level_domains
    from app.models.profile import CandidateProfile
    row = (await db.execute(select(CandidateProfile).where(
        CandidateProfile.user_id == user_id))).scalar_one_or_none()
    primary = code_for_domain_id(row.primary_domain_id) if row else None
    secondary = [code_for_domain_id(i) for i in (row.secondary_domain_ids or [])] if row else []
    return {
        "primary": primary,
        "secondary": [c for c in secondary if c],
        "available": [{"code": d.code, "name": d.name} for d in top_level_domains()],
    }


@router.put("/domains", summary="Declare target domain(s) — for career switchers whose resume is ambiguous")
async def set_target_domains(payload: dict = Body(...), user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.domains.catalog import domain_id, top_level_domains
    from app.models.profile import CandidateProfile

    valid = {d.code for d in top_level_domains()}
    primary = payload.get("primary")
    secondary = [c for c in (payload.get("secondary") or []) if c]
    if primary is not None and primary not in valid:
        raise HTTPException(422, f"Unknown domain code: {primary}")
    bad = [c for c in secondary if c not in valid]
    if bad:
        raise HTTPException(422, f"Unknown domain code(s): {bad}")

    row = (await db.execute(select(CandidateProfile).where(
        CandidateProfile.user_id == user_id))).scalar_one_or_none()
    if row is None:
        row = CandidateProfile(user_id=user_id)
        db.add(row)
    row.primary_domain_id = domain_id(primary) if primary else None
    row.secondary_domain_ids = [domain_id(c) for c in secondary]
    await db.flush()
    return {"primary": primary, "secondary": secondary, "updated": True}
