"""EMBEDHUNT AI — Auth API"""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.services.cache_warmer import warm_user_caches
from app.auth.permissions import get_current_user_id, get_token_payload
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, OtpRequest, RefreshRequest, ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/otp/request", summary="Send a registration OTP to a mobile number")
async def request_otp(req: OtpRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).request_otp(req.phone)

@router.post("/register", status_code=201, summary="Register a new user (requires verified mobile number)")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register(req.email, req.username, req.password, req.first_name, req.last_name, req.role, phone=req.phone, otp_code=req.otp_code)

@router.post("/login", summary="Login with email and password")
async def login(req: LoginRequest, request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    result = await AuthService(db).login(req.email, req.password, ip)
    user_id = (result.get("user") or {}).get("id")
    if user_id:
        background_tasks.add_task(warm_user_caches, user_id)
    return result

@router.post("/refresh", summary="Refresh access token")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).refresh(req.refresh_token)

@router.post("/verify-email", summary="Verify email with token")
async def verify_email(req: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    msg = await AuthService(db).verify_email(req.token)
    return {"message": msg}

@router.post("/forgot-password", summary="Request password reset")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    msg = await AuthService(db).forgot_password(req.email)
    return {"message": msg}

@router.post("/reset-password", summary="Reset password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    msg = await AuthService(db).reset_password(req.token, req.new_password)
    return {"message": msg}

@router.get("/me", summary="Get current user profile")
async def get_me(payload: dict = Depends(get_token_payload), db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    user_id = payload["sub"]
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    # Single active session: a token minted before the latest sign-in is dead.
    if payload.get("sv") is not None and payload["sv"] != (user.session_version or 0):
        raise HTTPException(401, "Session ended — this account signed in on another device")
    return {"id": user.id, "email": user.email, "username": user.username,
            "full_name": user.full_name, "role": user.role.value,
            "is_verified": user.is_verified, "is_premium": user.is_premium}


@router.get("/me/export", summary="Export my data (GDPR/DPDP)")
async def export_my_data(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """Everything we hold about the account, as one JSON document."""
    import json as _json
    from sqlalchemy import select
    from app.models.memory import MemoryEntry
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    out = {"user": {"id": user.id, "email": user.email, "username": user.username,
                    "full_name": user.full_name, "phone": user.phone,
                    "created_at": str(user.created_at)}}
    try:
        from app.repositories.resume_repository import ResumeRepository
        resumes = await ResumeRepository(db).list_for_user(user_id)
        out["resumes"] = [
            {"id": r.id, "name": r.name, "is_primary": r.is_primary,
             "profile": _json.loads(r.ai_summary) if r.ai_summary else None}
            for r in resumes]
    except Exception:
        out["resumes"] = []
    rows = (await db.execute(select(MemoryEntry).where(
        MemoryEntry.user_id == user_id))).scalars().all()
    out["memories"] = [{"type": m.memory_type, "content": m.content} for m in rows]
    return out


@router.delete("/me", summary="Delete my account (deactivate + scrub PII)")
async def delete_my_account(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    # Soft delete: deactivate and anonymise PII so FKs stay intact while the
    # person disappears. A scheduled hard-purge can follow retention policy.
    user.is_active = False
    user.email = f"deleted-{user.id}@removed.invalid"
    user.username = f"deleted-{user.id}"
    user.first_name, user.last_name = "Deleted", "User"
    user.phone = None
    user.phone_verified = False
    user.session_version = (user.session_version or 0) + 1  # kill sessions
    await db.flush()
    return {"deleted": True, "message": "Account deactivated and personal data scrubbed"}
