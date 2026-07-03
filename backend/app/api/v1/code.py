"""EMBEDHUNT AI — Code Reviewer API (Module 8).

Stateless static review of embedded C/C++. Code is analysed, never executed.
"""
from fastapi import APIRouter, Body, Depends, HTTPException

from app.ai.code_intelligence import CodeIntelligenceEngine
from app.auth.permissions import get_current_user_id

router = APIRouter(prefix="/code", tags=["Code Reviewer"])

_MAX_CODE_BYTES = 50_000
_engine = CodeIntelligenceEngine()


@router.post("/review", summary="Static review of embedded C/C++ source")
async def review_code(
    payload: dict = Body(..., example={"code": "void isr(){ x=1; }", "language": "c"}),
    user_id: str = Depends(get_current_user_id),
):
    code = payload.get("code") or ""
    language = (payload.get("language") or "c").lower()
    if not code.strip():
        raise HTTPException(422, "Field 'code' is required and cannot be empty.")
    if len(code.encode("utf-8")) > _MAX_CODE_BYTES:
        raise HTTPException(413, "Code exceeds the 50 KB review limit.")
    return _engine.review(code, language).to_dict()
