"""EMBEDHUNT AI — User Model"""
from typing import Optional
from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import BaseModel
from app.auth.permissions import UserRole

class User(BaseModel):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True, index=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Bumped on every login/registration; tokens carry it so only the most
    # recent sign-in per account (one person per mobile number) stays valid.
    session_version: Mapped[int] = mapped_column(default=0, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role_enum"), default=UserRole.CANDIDATE, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email_verify_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Job preferences
    min_salary_lpa: Mapped[float] = mapped_column(default=15.0, nullable=False)
    target_salary_lpa: Mapped[float] = mapped_column(default=20.0, nullable=False)
    preferred_locations: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    @property
    def full_name(self) -> str: return f"{self.first_name} {self.last_name}"
