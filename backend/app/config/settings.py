"""EMBEDHUNT AI — Central Settings"""
from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    APP_NAME: str = "EMBEDHUNT AI"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    SECRET_KEY: str = "dev-secret-minimum-32-chars-change-in-prod!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    CORS_ORIGINS: List[str] = ["http://localhost:3000","http://localhost:8080"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        return [o.strip() for o in v.split(",")] if isinstance(v, str) else v

    DATABASE_URL: str = "postgresql+asyncpg://embedhunt:embedhunt@localhost:5432/embedhunt"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_RESUMES: str = "embedhunt-resumes"

    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ── AI Career Mentor (Module 15) ────────────────────────────────────────
    # Optional LLM backend. When no key is set the mentor falls back to a
    # deterministic, CareerTwin-grounded advisor so the feature always works.
    ANTHROPIC_API_KEY: Optional[str] = None
    MENTOR_MODEL: str = "claude-3-5-sonnet-latest"
    MENTOR_MAX_TOKENS: int = 700

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM: str = "noreply@embedhunt.ai"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    DEFAULT_MIN_SALARY_LPA: float = 15.0
    DEFAULT_TARGET_SALARY_LPA: float = 20.0
    SCAN_INTERVAL_MINUTES: int = 30
    MAX_JOBS_PER_SCAN: int = 500

    FEATURE_AUTO_APPLY: bool = False
    FEATURE_AI_MATCHING: bool = True
    FEATURE_INTERVIEW_GEN: bool = True

    # ── Mobile in-app update channel ────────────────────────────────────────
    # Secret required to POST a new version to /api/v1/app/version/update.
    # Set this in the environment; CI uses it to publish new releases.
    APP_UPDATE_SECRET: str = "change-me-mobile-update-secret"
    # Where the current published mobile version config is persisted. The file
    # is written by CI after a successful release and read by every app.
    MOBILE_VERSION_FILE: str = "mobile_version.json"
    # Fallback / initial values served before CI has published anything.
    MOBILE_LATEST_VERSION: str = "1.0.0"
    MOBILE_VERSION_CODE: int = 10000
    MOBILE_APK_URL: str = ""
    MOBILE_MIN_SUPPORTED_VERSION: str = "1.0.0"

    @property
    def is_production(self) -> bool: return self.APP_ENV == "production"

    @property
    def database_url_sync(self) -> str: return self.DATABASE_URL.replace("+asyncpg", "")

@lru_cache()
def get_settings() -> Settings: return Settings()
settings = get_settings()
