"""EMBEDHUNT AI — Auth Schemas"""
import re
from pydantic import BaseModel, EmailStr, field_validator
from app.auth.permissions import UserRole

class RegisterRequest(BaseModel):
    email: EmailStr; username: str; password: str; first_name: str; last_name: str
    role: UserRole = UserRole.CANDIDATE
    phone: str | None = None
    otp_code: str | None = None

    @field_validator("username")
    @classmethod
    def val_username(cls, v):
        v = v.strip().lower()
        if len(v) < 3 or len(v) > 30: raise ValueError("Username: 3-30 chars")
        if not re.match(r"^[a-z0-9_-]+$", v): raise ValueError("Alphanumeric, underscore, hyphen only")
        return v

    @field_validator("password")
    @classmethod
    def val_password(cls, v):
        if len(v) < 8: raise ValueError("Min 8 chars")
        if not re.search(r"[A-Z]", v): raise ValueError("Need uppercase")
        if not re.search(r"[0-9]", v): raise ValueError("Need digit")
        return v

class LoginRequest(BaseModel):
    email: EmailStr; password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str; new_password: str

class VerifyEmailRequest(BaseModel):
    token: str


class OtpRequest(BaseModel):
    phone: str
