"""EMBEDHUNT AI — Open-Model engine (Together AI hosted, or local-capable).

The mid-tier :class:`InferenceEngine` between the knowledge graph and Claude —
the "Local LLMs" tier of the architecture. It calls an **open model fleet**
(Qwen / Llama / Gemma / Mistral, picked per task by
:mod:`app.orchestrator.task_registry`) through an **OpenAI-compatible**
``/chat/completions`` endpoint.

Provider is pluggable via config, over one code path:

* ``OPEN_MODEL_PROVIDER=together`` (default) → hosted open models on Together AI.
* ``OPEN_MODEL_PROVIDER=local`` + ``OPEN_MODEL_BASE_URL=http://localhost:11434/v1``
  → a genuinely self-hosted fleet on Ollama / vLLM (no API key required).

Flow: sanitize the payload (PII), call the provider, then score a **deliberately
simple** confidence heuristic. If the score clears
``ORCHESTRATOR_HOSTED_MODEL_MIN_CONFIDENCE`` the answer is returned; otherwise
the engine returns ``confidence=None`` so the Orchestrator escalates to Claude.
Whether a task is attempted at all is gated by the allowlist in
:mod:`app.orchestrator.task_registry`.

NOTE (v1): the confidence heuristic below (JSON-parseability for structured
tasks; length / truncation / repetition sanity checks for freeform) is
intentionally basic. It is a placeholder for a proper eval-based confidence
model later — do not over-invest in it now.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from app.config.logging import get_logger
from app.config.settings import settings
from app.orchestrator.engine_base import EngineResult, InferenceEngine
from app.orchestrator.task_registry import is_hosted_allowed, is_structured_output, model_for_task

logger = get_logger(__name__)

# Per-model pricing, USD per 1K tokens (input, output). Together AI published
# rates as of 2026-07 — VERIFY PERIODICALLY at https://www.together.ai/pricing.
# Local providers are effectively free; _DEFAULT_PRICE covers unlisted models.
_DEFAULT_PRICE = (0.00088, 0.00088)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "Qwen/Qwen2.5-72B-Instruct-Turbo": (0.0012, 0.0012),
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": (0.00088, 0.00088),
    "google/gemma-2-27b-it": (0.0008, 0.0008),
    "mistralai/Mixtral-8x7B-Instruct-v0.1": (0.0006, 0.0006),
}

# ── PII / data governance ───────────────────────────────────────────────────
# DATA GOVERNANCE REQUIREMENT: raw PII must never leave our infra for a
# third-party inference provider unchecked. Before any Together AI call we strip
# obvious identity fields from the payload and redact inline email/phone
# patterns from the remaining free text. This v1 pass is lightweight (labelled
# keys + regex) — a stricter NER-based scrubber (names, addresses) is a
# follow-up; bulk bodies like resume_text are still forwarded for tasks that
# need them, minus inline identifiers.
_PII_KEYS = frozenset(
    {
        "name", "full_name", "first_name", "last_name", "candidate_name",
        "email", "emails", "email_address", "phone", "phone_number", "mobile",
        "address", "street_address", "location_address", "linkedin",
        "linkedin_url", "github", "github_url", "ssn", "dob", "date_of_birth",
        "passport", "national_id",
    }
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")


def scrub_pii(text: str) -> str:
    """Redact inline emails/phones from free text (shared PII scrubber)."""
    if not isinstance(text, str):
        return text
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


class HostedModelEngine(InferenceEngine):
    """Together AI open-model engine with confidence-gated escalation to Claude."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        min_confidence: Optional[float] = None,
        timeout: Optional[float] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enabled: Optional[bool] = None,
    ):
        # Provider/endpoint/key resolve to Together by default, but OPEN_MODEL_*
        # overrides let the same code path target a local Ollama/vLLM server.
        self._provider = provider or settings.OPEN_MODEL_PROVIDER
        self._api_key = (
            api_key if api_key is not None
            else (settings.OPEN_MODEL_API_KEY or settings.TOGETHER_API_KEY)
        )
        self._base_url = base_url or settings.OPEN_MODEL_BASE_URL or settings.TOGETHER_BASE_URL
        self._model = model or settings.TOGETHER_MODEL  # default; per-task overrides in registry
        self._min_confidence = (
            min_confidence if min_confidence is not None
            else settings.ORCHESTRATOR_HOSTED_MODEL_MIN_CONFIDENCE
        )
        self._timeout = timeout if timeout is not None else settings.HOSTED_MODEL_TIMEOUT_SECONDS
        self._max_tokens = max_tokens or settings.HOSTED_MODEL_MAX_TOKENS
        self._temperature = (
            temperature if temperature is not None else settings.HOSTED_MODEL_TEMPERATURE
        )
        self._enabled = enabled if enabled is not None else settings.ORCHESTRATOR_ENABLE_HOSTED_MODEL

    def _model_for(self, task: str) -> str:
        """Open model assigned to ``task`` (fleet routing), or the default."""
        return model_for_task(task, self._model)

    @property
    def _needs_key(self) -> bool:
        """Self-hosted providers (local / shadow candidate) need no API key."""
        return self._provider not in ("local", "shadow")

    async def run(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        """Attempt ``task`` on the hosted model, or return ``None`` to fall through.

        Returns ``None`` when the engine is disabled, unconfigured, the task is
        not on the allowlist, or the API call fails. Otherwise it always returns
        an :class:`EngineResult` carrying real token/cost figures (so the call is
        billed even when escalated); ``confidence`` is the heuristic score when
        accepted, or ``None`` to signal escalation to Claude.
        """
        if not is_hosted_allowed(task):
            # Defense in depth — the router already gates on the allowlist.
            return None
        return await self._infer(task, payload, context or {})

    async def generate(
        self, task: str, payload: dict, context: Optional[dict] = None
    ) -> Optional[EngineResult]:
        """Run the configured model for ``task`` **without** the allowlist gate,
        forcing this engine's own model (not fleet routing).

        Used for shadow capture: score a candidate model on any task we want to
        evaluate, regardless of the production routing table.
        """
        return await self._infer(task, payload, context or {}, model=self._model)

    async def _infer(
        self, task: str, payload: dict, context: dict, *, model: Optional[str] = None
    ) -> Optional[EngineResult]:
        if not self._enabled or (self._needs_key and not self._api_key):
            return None
        model = model or self._model_for(task)
        max_tokens = int(payload.get("max_tokens") or self._max_tokens)
        messages = self._build_messages(payload, context)
        completion = await self._chat_completion(messages, model, max_tokens)
        if completion is None:
            return None  # network / provider error → let the router escalate to Claude

        text = completion["content"]
        tokens_in = completion["tokens_in"]
        tokens_out = completion["tokens_out"]
        cost = self._estimate_cost(tokens_in, tokens_out, model)
        score = self._score_confidence(task, text, completion.get("finish_reason"))
        accepted = score >= self._min_confidence
        logger.info(
            "orchestrator_open_model",
            task=task,
            provider=self._provider,
            model=model,
            confidence=round(score, 3),
            accepted=accepted,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
        )
        return EngineResult(
            text=text,
            engine_used=f"{self._provider}:{model}",
            confidence=score if accepted else None,  # None → router escalates to Claude
            cached=False,
            cost_estimate_usd=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    # ── provider call ───────────────────────────────────────────────────────
    async def _chat_completion(
        self, messages: list[dict], model: str, max_tokens: Optional[int] = None
    ) -> Optional[dict]:
        """POST to the OpenAI-compatible endpoint; normalise the response.

        Returns ``{content, tokens_in, tokens_out, finish_reason}`` or ``None``
        on any transport/parse failure (best-effort — never raises).
        """
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or self._max_tokens,
            "temperature": self._temperature,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 — any failure → escalate to Claude
            logger.warning("hosted_model_request_failed", model=self._model, error=str(exc))
            return None
        try:
            choice = data["choices"][0]
            usage = data.get("usage") or {}
            return {
                "content": choice["message"]["content"] or "",
                "tokens_in": int(usage.get("prompt_tokens", 0) or 0),
                "tokens_out": int(usage.get("completion_tokens", 0) or 0),
                "finish_reason": choice.get("finish_reason"),
            }
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("hosted_model_bad_response", model=self._model, error=str(exc))
            return None

    def _estimate_cost(self, tokens_in: int, tokens_out: int, model: Optional[str] = None) -> float:
        price_in, price_out = _MODEL_PRICING.get(model or self._model, _DEFAULT_PRICE)
        if self._provider == "local":  # self-hosted → no per-token vendor cost
            price_in = price_out = 0.0
        return round((tokens_in / 1000) * price_in + (tokens_out / 1000) * price_out, 6)

    # ── message construction (with PII sanitisation) ────────────────────────
    def _build_messages(self, payload: dict, context: dict) -> list[dict]:
        sanitized = self._sanitize_payload(payload)
        system = sanitized.get("system") or context.get("system") or ""
        raw_messages = sanitized.get("messages")
        if isinstance(raw_messages, list) and raw_messages:
            messages = [m for m in raw_messages if m.get("role") != "system"]
        else:
            prompt = sanitized.get("prompt") or sanitized.get("input")
            if not prompt:
                prompt = json.dumps(sanitized, sort_keys=True, default=str)
            messages = [{"role": "user", "content": prompt}]
        if system:
            messages = [{"role": "system", "content": system}, *messages]
        return messages

    @classmethod
    def _sanitize_payload(cls, payload: dict) -> dict:
        """Drop obvious PII keys and redact inline emails/phones. See governance
        note at the top of this module."""
        clean: dict = {}
        for key, value in payload.items():
            if key.lower() in _PII_KEYS:
                continue  # drop labelled identity fields entirely
            clean[key] = cls._redact_value(value)
        return clean

    @classmethod
    def _redact_value(cls, value):
        if isinstance(value, str):
            return scrub_pii(value)
        if isinstance(value, list):
            return [cls._redact_value(v) for v in value]
        if isinstance(value, dict):
            return {
                k: ("[REDACTED_PII]" if k.lower() in _PII_KEYS else cls._redact_value(v))
                for k, v in value.items()
            }
        return value

    # ── confidence heuristic (v1 — see module docstring) ────────────────────
    def _score_confidence(self, task: str, text: str, finish_reason: Optional[str]) -> float:
        text = (text or "").strip()
        if not text:
            return 0.0
        if is_structured_output(task):
            return self._json_confidence(text)
        return self._freeform_confidence(text, finish_reason)

    @staticmethod
    def _json_confidence(text: str) -> float:
        candidate = _strip_code_fence(text)
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            return 0.2  # not valid JSON — structured task failed, escalate
        if isinstance(parsed, (dict, list)) and parsed:
            return 0.95
        return 0.5  # valid but empty ({} / [])

    @staticmethod
    def _freeform_confidence(text: str, finish_reason: Optional[str]) -> float:
        words = text.split()
        if len(text) < 40 or len(words) < 8:
            return 0.35  # too short to be a real answer
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        if unique_ratio < 0.35:
            return 0.2  # degenerate repeated-token / loop output
        if finish_reason == "length":
            return 0.5  # truncated mid-thought
        return 0.9


def _strip_code_fence(text: str) -> str:
    """Strip a leading/trailing markdown code fence (```json … ```), if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9]*\s*", "", stripped)
        if stripped.endswith("```"):
            stripped = stripped[: -3]
    return stripped.strip()


# The engine represents the open-model tier (hosted fleet by default, local-capable).
# ``OpenModelEngine`` is the preferred name; ``HostedModelEngine`` is kept for
# backward compatibility with existing imports.
OpenModelEngine = HostedModelEngine
