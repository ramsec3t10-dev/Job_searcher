"""EMBEDHUNT AI — Auth API"""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.services.cache_warmer import warm_user_caches
from app.auth.permissions import get_current_user_id
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=201, summary="Register a new user")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register(req.email, req.username, req.password, req.first_name, req.last_name, req.role)

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
async def get_me(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        from fastapi import HTTPException; raise HTTPException(404, "User not found")
    return {"id": user.id, "email": user.email, "username": user.username,
            "full_name": user.full_name, "role": user.role.value,
            "is_verified": user.is_verified, "is_premium": user.is_premium}
