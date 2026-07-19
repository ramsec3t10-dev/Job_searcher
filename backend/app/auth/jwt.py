"""EMBEDHUNT AI — JWT Token Engine"""
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.config.settings import settings

class TokenType(str, Enum):
    ACCESS = "access"; REFRESH = "refresh"
    EMAIL_VERIFY = "email_verify"; PASSWORD_RESET = "password_reset"

def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta, extra: dict = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "type": token_type.value, "iat": now, "exp": now + expires_delta, "jti": str(uuid.uuid4())}
    if extra: payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_access_token(user_id: str, role: str, session_version: int = 0) -> str:
    return _create_token(user_id, TokenType.ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), {"role": role, "sv": session_version})

def create_refresh_token(user_id: str, session_version: int = 0) -> str:
    return _create_token(user_id, TokenType.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), {"sv": session_version})

def create_email_verify_token(email: str) -> str:
    return _create_token(email, TokenType.EMAIL_VERIFY, timedelta(hours=24))

def create_password_reset_token(email: str) -> str:
    return _create_token(email, TokenType.PASSWORD_RESET, timedelta(hours=1))

def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type.value or payload.get("sub") is None: raise exc
        return payload
    except JWTError: raise exc
