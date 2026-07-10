"""EMBEDHUNT AI — Test Configuration"""
import os
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-chars-embedhunt!!"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["APP_ENV"] = "test"
os.environ["LOG_FORMAT"] = "text"
os.environ["LOG_LEVEL"] = "WARNING"
# AI enrichment stays on in tests (Bedrock is always mocked); a dummy key
# satisfies the startup config validation without contacting AWS.
os.environ.setdefault("BEDROCK_API_KEY", "test-bedrock-key")
