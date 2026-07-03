"""EMBEDHUNT AI — Career Mentor API (Module 15)."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import get_current_user_id
from app.database.session import get_db
from app.services.mentor_service import MentorService

router = APIRouter(prefix="/mentor", tags=["Career Mentor"])


@router.post("/chat", summary="Ask the AI Career Mentor a question")
async def mentor_chat(
    payload: dict = Body(..., example={"message": "How do I get into Qualcomm?", "history": []}),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(422, "Field 'message' is required.")
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    return await MentorService(db).chat(user_id, message, history)
