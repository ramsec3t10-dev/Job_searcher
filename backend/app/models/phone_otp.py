"""EMBEDHUNT AI — Phone OTP staging table (pre-registration verification)."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseModel


class PhoneOtp(BaseModel):
    __tablename__ = "phone_otps"
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(50), nullable=False)  # ISO UTC
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
