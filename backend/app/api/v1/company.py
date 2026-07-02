"""EMBEDHUNT AI — Company Intelligence API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.company_service import CompanyService
from app.services.company_intel_service import CompanyIntelligenceService

router = APIRouter(prefix="/company", tags=["Company Intelligence"])

@router.get("/intelligence", summary="All monitored companies and portals")
async def get_intelligence():
    return CompanyService().get_intelligence_report()

@router.get("/fit", summary="Company fit analysis")
async def get_fit(company: str = Query(...), score: int = Query(50), skills: str = Query("")):
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    return CompanyService().get_company_fit(company, skill_list, score)

@router.get("/list", summary="Enriched company profiles (optionally filtered by tier)")
async def list_companies(tier: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    return await CompanyIntelligenceService(db).list_companies(tier=tier)

@router.get("/profile", summary="Full company intelligence profile + live application stats")
async def get_company_profile(company: str = Query(...), db: AsyncSession = Depends(get_db)):
    return await CompanyIntelligenceService(db).get_company_intel(company)
