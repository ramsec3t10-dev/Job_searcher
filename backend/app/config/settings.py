"""EMBEDHUNT AI — Central Settings"""
from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator, model_validator
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

    # ── Phone OTP registration ──────────────────────────────────────────
    # When True, registration requires a mobile number verified via OTP.
    # SMS delivery uses Twilio when creds are set; otherwise (dev) the code
    # is returned in the API response as `dev_code`.
    OTP_REQUIRED: bool = True
    OTP_TTL_SECONDS: int = 300
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None

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

    # ── LLM Foundation (AWS Bedrock / Anthropic) ────────────────────────────
    # Optional API credentials; when unset the app still starts and the LLM
    # layer stays dormant until wired in. Model routing is configured here so
    # the routing table is data-driven, not hardcoded in the selector.
    BEDROCK_API_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_MAX_MONTHLY_COST_USD: float = 2.0
    LLM_HAIKU_MODEL: str = "claude-haiku-4-5"
    LLM_SONNET_MODEL: str = "claude-sonnet-4-6"
    LLM_OPUS_MODEL: str = "claude-opus-4-8"

    LLM_ENRICHMENT_ENABLED: bool = True  # master toggle for all AI enrichment
    LLM_ENRICHMENT_TIMEOUT_SECONDS: int = 10  # if AI takes longer, use fallback

    # ── AI Orchestrator (Phase 1) ───────────────────────────────────────────
    # Per-task exact-match cache TTL (seconds) for the orchestrator. Tasks not
    # listed fall back to a 1-day (86400s) default; a value of 0 disables
    # caching for that task. ORCHESTRATOR_ENABLE_CACHE is the master on/off
    # switch for the orchestrator's cache layer.
    ORCHESTRATOR_CACHE_TTL: dict[str, int] = {}
    ORCHESTRATOR_ENABLE_CACHE: bool = True
    # Semantic (embedding-similarity) cache: serve a near-duplicate cached result
    # when the exact-match key misses. Uses app.ai.embeddings (offline-capable).
    ORCHESTRATOR_SEMANTIC_CACHE: bool = True
    ORCHESTRATOR_SEMANTIC_CACHE_THRESHOLD: float = 0.92
    # Bound the per-task embedding index (cosine scan cost + memory). Oldest
    # entries are trimmed past this cap; entries also expire with the cache TTL.
    ORCHESTRATOR_SEMANTIC_CACHE_MAX_PER_TASK: int = 500

    # ── AI Orchestrator — Hosted Open-Model Engine (Phase 3) ────────────────
    # Mid-tier engine between the knowledge graph and Claude, calling a hosted
    # open model via Together AI's OpenAI-compatible API. The key is sourced
    # from the environment only (never hardcoded); when unset the engine stays
    # dormant and the orchestrator falls straight through to Claude.
    TOGETHER_API_KEY: Optional[str] = None
    TOGETHER_BASE_URL: str = "https://api.together.xyz/v1"
    # Default open model (per-task overrides live in task_registry OPEN_MODEL_TASK_MODELS).
    TOGETHER_MODEL: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    # Provider/endpoint are pluggable: keep "together" (hosted) OR point at a
    # local OpenAI-compatible server (Ollama/vLLM) for a genuinely self-hosted
    # open-model tier — same code path, no key required for local.
    #   e.g. OPEN_MODEL_PROVIDER=local  OPEN_MODEL_BASE_URL=http://localhost:11434/v1
    OPEN_MODEL_PROVIDER: str = "together"          # "together" | "local" | any label
    OPEN_MODEL_BASE_URL: Optional[str] = None      # overrides TOGETHER_BASE_URL when set
    OPEN_MODEL_API_KEY: Optional[str] = None       # overrides TOGETHER_API_KEY (local: leave unset)
    ORCHESTRATOR_ENABLE_HOSTED_MODEL: bool = True  # master on/off for the open-model engine
    # Below this heuristic confidence the hosted answer is discarded and the
    # request escalates to Claude (see hosted_model_engine._score_confidence).
    ORCHESTRATOR_HOSTED_MODEL_MIN_CONFIDENCE: float = 0.6
    HOSTED_MODEL_TIMEOUT_SECONDS: float = 30.0
    HOSTED_MODEL_MAX_TOKENS: int = 1024
    HOSTED_MODEL_TEMPERATURE: float = 0.3

    # ── AI Orchestrator — Training capture & distillation (Phase 5) ─────────
    # Off by default (privacy-safe). When ON, every paid engine result is
    # captured (PII-scrubbed) to ai_interaction as training data — but ONLY for
    # requests that carry user consent (context["consent"]=True).
    ORCHESTRATOR_CAPTURE_TRAINING_DATA: bool = False
    # Shadow routing: after serving the real answer, also run a candidate model
    # (your own fine-tune) and log its output WITHOUT serving it — so you gather
    # candidate-vs-incumbent data risk-free. Requires capture to be on.
    ORCHESTRATOR_SHADOW_MODEL_ENABLED: bool = False
    SHADOW_MODEL_PROVIDER: str = "shadow"
    SHADOW_MODEL_BASE_URL: Optional[str] = None   # your candidate inference endpoint (OpenAI-compatible)
    SHADOW_MODEL_API_KEY: Optional[str] = None
    SHADOW_MODEL_NAME: str = "embedhunt-distill-v0"

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
    APP_UPDATE_SECRET: str = "embedhunt-update-secret-2026"
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

    @model_validator(mode="after")
    def validate_bedrock_config(self):
        """Fail fast at startup if AI enrichment is on but Bedrock is unconfigured."""
        if self.LLM_ENRICHMENT_ENABLED:
            if not self.BEDROCK_API_KEY:
                raise ValueError("BEDROCK_API_KEY required when LLM_ENRICHMENT_ENABLED=True")
            if not self.AWS_REGION:
                raise ValueError("AWS_REGION required when LLM_ENRICHMENT_ENABLED=True")
        return self

@lru_cache()
def get_settings() -> Settings: return Settings()
settings = get_settings()
