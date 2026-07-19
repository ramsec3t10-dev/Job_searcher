"""EMBEDHUNT AI — Embedded Coding Lab API (Module 7)."""
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.auth.permissions import get_current_user_id
from app.lab.challenges import get_challenge, list_challenges
from app.lab.evaluator import LabEvaluator

router = APIRouter(prefix="/lab", tags=["Coding Lab"])

_evaluator = LabEvaluator()
_MAX_CODE_BYTES = 50_000


@router.get("/challenges", summary="List coding-lab challenges")
async def challenges(
    difficulty: str | None = Query(None, description="easy | medium | hard"),
    user_id: str = Depends(get_current_user_id),
):
    return {"challenges": list_challenges(difficulty)}


@router.get("/challenges/{challenge_id}", summary="Get a single challenge")
async def challenge_detail(
    challenge_id: str,
    reveal: bool = False,
    user_id: str = Depends(get_current_user_id),
):
    """Challenge body; pass ``reveal=true`` for the reference solution and
    interviewer notes (training mode)."""
    ch = get_challenge(challenge_id)
    if not ch:
        raise HTTPException(404, f"Challenge {challenge_id} not found.")
    return ch.detail() if reveal else ch.public()


@router.post("/challenges/{challenge_id}/submit", summary="Submit a solution for static grading")
async def submit_solution(
    challenge_id: str,
    payload: dict = Body(..., example={"code": "void set_bit(...){...}"}),
    user_id: str = Depends(get_current_user_id),
):
    ch = get_challenge(challenge_id)
    if not ch:
        raise HTTPException(404, f"Challenge {challenge_id} not found.")
    code = payload.get("code") or ""
    if not code.strip():
        raise HTTPException(422, "Field 'code' is required and cannot be empty.")
    if len(code.encode("utf-8")) > _MAX_CODE_BYTES:
        raise HTTPException(413, "Code exceeds the 50 KB limit.")
    return _evaluator.evaluate(ch, code)
