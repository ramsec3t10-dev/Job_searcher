"""EMBEDHUNT AI — AWS Bedrock (Anthropic) async client.

Wraps AnthropicBedrock with production concerns: bounded retries with
exponential backoff, per-tier timeouts, a circuit breaker, and structured
telemetry. The anthropic SDK is imported lazily so the package remains
importable in environments where it is not installed.
"""
from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, AsyncIterator, Optional

from app.config.logging import get_logger
from app.config.settings import settings
from app.core.exceptions import EmbedHuntException

logger = get_logger(__name__)

_TIMEOUTS = {"haiku": 30.0, "sonnet": 60.0, "opus": 120.0}


class BedrockError(EmbedHuntException):
    def __init__(self, message: str):
        super().__init__(message, 502)


class CircuitOpenError(BedrockError):
    def __init__(self):
        super().__init__("Bedrock circuit breaker is open")


def _timeout_for(model_id: str) -> float:
    m = model_id.lower()
    if "haiku" in m:
        return _TIMEOUTS["haiku"]
    if "opus" in m:
        return _TIMEOUTS["opus"]
    return _TIMEOUTS["sonnet"]


class _CircuitBreaker:
    def __init__(self, threshold: int = 5, reset_seconds: int = 60):
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.failures = 0
        self.opened_at = 0.0

    def allow(self) -> bool:
        if self.failures < self.threshold:
            return True
        if time.time() - self.opened_at >= self.reset_seconds:
            self.failures = self.threshold - 1  # half-open: allow a probe
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.time()


class BedrockClient:
    def __init__(self, api_key: Optional[str] = None, region: Optional[str] = None, max_retries: int = 3):
        self.api_key = api_key if api_key is not None else settings.BEDROCK_API_KEY
        self.region = region or settings.AWS_REGION
        self.max_retries = max_retries
        self._client = None
        self._breaker = _CircuitBreaker()

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropicBedrock
            except ImportError as exc:
                raise BedrockError("anthropic package is not installed") from exc
            if self.api_key:
                os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", self.api_key)
            self._client = AsyncAnthropicBedrock(aws_region=self.region)
        return self._client

    async def invoke_model(
        self,
        model_id: str,
        messages: list,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        if not self._breaker.allow():
            raise CircuitOpenError()
        timeout = timeout or _timeout_for(model_id)
        last_err: Optional[Exception] = None
        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            start = time.perf_counter()
            try:
                client = self._get_client()
                kwargs: dict[str, Any] = {
                    "model": model_id,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages,
                }
                if system:
                    kwargs["system"] = system
                resp = await asyncio.wait_for(client.messages.create(**kwargs), timeout=timeout)
                latency = round((time.perf_counter() - start) * 1000, 2)
                content = "".join(
                    getattr(block, "text", "") for block in resp.content if getattr(block, "type", None) == "text"
                )
                usage = getattr(resp, "usage", None)
                input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
                output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
                self._breaker.record_success()
                logger.info(
                    "bedrock_invoke",
                    model=model_id,
                    latency_ms=latency,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": latency,
                    "model": model_id,
                }
            except CircuitOpenError:
                raise
            except Exception as exc:  # noqa: BLE001 — retry policy handles all failures
                last_err = exc
                self._breaker.record_failure()
                logger.warning("bedrock_invoke_failed", model=model_id, attempt=attempt, error=str(exc))
                if attempt >= self.max_retries or not self._breaker.allow():
                    break
                backoff = min(8.0, 0.5 * (2 ** (attempt - 1)) + random.random() * 0.25)
                await asyncio.sleep(backoff)
        logger.error("bedrock_invoke_error", model=model_id, error=str(last_err))
        raise BedrockError(f"invoke_model failed after {attempt} attempts: {last_err}")

    async def invoke_model_stream(
        self,
        model_id: str,
        messages: list,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[str]:
        if not self._breaker.allow():
            raise CircuitOpenError()
        start = time.perf_counter()
        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                "model": model_id,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
            self._breaker.record_success()
            logger.info("bedrock_stream", model=model_id, latency_ms=round((time.perf_counter() - start) * 1000, 2))
        except Exception as exc:  # noqa: BLE001
            self._breaker.record_failure()
            logger.error("bedrock_stream_error", model=model_id, error=str(exc))
            raise BedrockError(f"invoke_model_stream failed: {exc}")
