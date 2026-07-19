"""EMBEDHUNT AI — Auth Service"""
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.jwt import create_access_token, create_refresh_token, create_email_verify_token, create_password_reset_token, decode_token, TokenType
from app.auth.password import hash_password, verify_password
from app.auth.permissions import UserRole
from app.repositories.user_repository import UserRepository
from app.config.logging import get_logger
from app.common.constants import MAX_FAILED_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES

logger = get_logger(__name__)

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(c for c in (phone or "") if c.isdigit() or c == "+")
        if not digits.startswith("+"):
            digits = "+" + digits
        if len(digits) < 11:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Enter a valid mobile number with country code")
        return digits

    async def request_otp(self, phone: str) -> dict:
        """Issue a 6-digit code for this phone (5-minute TTL). In dev (no SMS
        provider) the code is returned as `dev_code` so the flow stays real."""
        import hashlib, secrets
        from app.config.settings import settings
        from app.models.phone_otp import PhoneOtp
        from app.models.user import User
        from app.services.sms_service import send_sms
        from sqlalchemy import select

        phone = self._normalize_phone(phone)
        existing = (await self.db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "This mobile number is already registered")
        code = f"{secrets.randbelow(1_000_000):06d}"
        row = (await self.db.execute(select(PhoneOtp).where(PhoneOtp.phone == phone))).scalar_one_or_none()
        if row is None:
            row = PhoneOtp(phone=phone)
            self.db.add(row)
        row.code_hash = hashlib.sha256(code.encode()).hexdigest()
        row.expires_at = (datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)).isoformat()
        row.attempts = 0
        await self.db.flush()
        sent = await send_sms(phone, f"Your EMBEDHUNT verification code is {code}")
        out = {"message": "Verification code sent", "expires_in": settings.OTP_TTL_SECONDS}
        if not sent and not settings.is_production:
            out["dev_code"] = code
        logger.info("otp_requested", phone_last4=phone[-4:], sent=sent)
        return out

    async def _consume_otp(self, phone: str, code: str) -> None:
        import hashlib
        from app.models.phone_otp import PhoneOtp
        from sqlalchemy import select

        row = (await self.db.execute(select(PhoneOtp).where(PhoneOtp.phone == phone))).scalar_one_or_none()
        bad = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification code")
        if row is None:
            raise bad
        if datetime.now(timezone.utc) > datetime.fromisoformat(row.expires_at) or row.attempts >= 5:
            await self.db.delete(row); await self.db.flush()
            raise bad
        if hashlib.sha256((code or "").encode()).hexdigest() != row.code_hash:
            row.attempts += 1; await self.db.flush()
            raise bad
        await self.db.delete(row); await self.db.flush()

    async def register(self, email: str, username: str, password: str, first_name: str, last_name: str, role: UserRole = UserRole.CANDIDATE, phone: str | None = None, otp_code: str | None = None) -> dict:
        from app.config.settings import settings
        if await self.repo.email_exists(email.lower()):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        if await self.repo.username_exists(username.lower()):
            raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
        verified_phone: str | None = None
        if settings.OTP_REQUIRED:
            if not phone or not otp_code:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mobile number and verification code are required")
            verified_phone = self._normalize_phone(phone)
            await self._consume_otp(verified_phone, otp_code)
        user = await self.repo.create(
            email=email.lower(), username=username.lower(),
            password_hash=hash_password(password),
            first_name=first_name.strip(), last_name=last_name.strip(),
            role=role, is_active=True, is_verified=False,
            phone=verified_phone, phone_verified=verified_phone is not None,
            session_version=1,
        )
        token = create_email_verify_token(user.email)
        await self.repo.set_verify_token(user.id, token)
        logger.info("user_registered", user_id=user.id, role=role.value)
        return self._tokens_and_user(user, "Registration successful")

    async def login(self, email: str, password: str, ip: str = "unknown") -> dict:
        user = await self.repo.get_by_email(email.lower())
        _err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
        if not user: raise _err
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")
        if user.locked_until:
            locked = datetime.fromisoformat(user.locked_until)
            if datetime.now(timezone.utc) < locked:
                mins = int((locked - datetime.now(timezone.utc)).total_seconds() / 60) + 1
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Account locked. Try in {mins} min.")
        if not verify_password(password, user.password_hash):
            n = await self.repo.increment_failed_login(user.id)
            if n >= MAX_FAILED_LOGIN_ATTEMPTS:
                until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
                await self.repo.set_locked_until(user.id, until)
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many failures. Locked {LOCKOUT_DURATION_MINUTES} min.")
            raise _err
        await self.repo.update_last_login(user.id)
        # One active session per account/mobile number: invalidate all
        # previously issued tokens by bumping the session version.
        user.session_version = (user.session_version or 0) + 1
        await self.db.flush()
        logger.info("user_login", user_id=user.id, ip=ip, sv=user.session_version)
        return self._tokens_and_user(user, "Login successful")

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token, TokenType.REFRESH)
        user = await self.repo.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        if payload.get("sv") is not None and payload["sv"] != (user.session_version or 0):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session ended — this account signed in on another device")
        from app.config.settings import settings
        return {"access_token": create_access_token(user.id, user.role.value, user.session_version or 0),
                "refresh_token": create_refresh_token(user.id, user.session_version or 0),
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

    async def verify_email(self, token: str) -> str:
        payload = decode_token(token, TokenType.EMAIL_VERIFY)
        user = await self.repo.get_by_email(payload["sub"])
        if not user: raise HTTPException(404, "User not found")
        if user.is_verified: return "Already verified"
        await self.repo.verify_email(user.id)
        return "Email verified successfully"

    async def forgot_password(self, email: str) -> str:
        user = await self.repo.get_by_email(email.lower())
        if user:
            token = create_password_reset_token(user.email)
            await self.repo.set_reset_token(user.id, token)
        return "If that email exists, a reset link was sent"

    async def reset_password(self, token: str, new_password: str) -> str:
        payload = decode_token(token, TokenType.PASSWORD_RESET)
        user = await self.repo.get_by_email(payload["sub"])
        if not user: raise HTTPException(404, "User not found")
        await self.repo.update_password(user.id, hash_password(new_password))
        return "Password reset successfully"

    def _tokens_and_user(self, user, message: str) -> dict:
        from app.config.settings import settings
        return {
            "access_token": create_access_token(user.id, user.role.value, user.session_version or 0),
            "refresh_token": create_refresh_token(user.id, user.session_version or 0),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id, "email": user.email, "username": user.username,
                "first_name": user.first_name, "last_name": user.last_name,
                "full_name": user.full_name, "role": user.role.value,
                "is_verified": user.is_verified, "is_premium": user.is_premium,
            },
            "message": message
        }
