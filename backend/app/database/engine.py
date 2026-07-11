"""EMBEDHUNT AI — Database Engine"""
from sqlalchemy.ext.asyncio import create_async_engine
from app.config.settings import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)
