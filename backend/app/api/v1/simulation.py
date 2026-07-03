"""EMBEDHUNT AI — Career Simulation API (Module 13)."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["Career Simulation"])


@router.post("/what-if", summary="Simulate learning skills and/or gaining experience")
async def what_if(
    payload: dict = Body(
        default={},
        example={"learn_skills": ["AUTOSAR", "ISO 26262"], "extra_years": 1},
    ),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    learn_skills = payload.get("learn_skills") or []
    extra_years = float(payload.get("extra_years") or 0.0)
    return await SimulationService(db).simulate(
        user_id, learn_skills=learn_skills, extra_years=extra_years
    )


@router.get("/skill/{skill_name}", summary="Impact of learning a single skill")
async def simulate_skill(
    skill_name: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await SimulationService(db).simulate(user_id, learn_skills=[skill_name])
