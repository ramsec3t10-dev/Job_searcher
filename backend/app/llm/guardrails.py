"""EMBEDHUNT AI — LLM Guardrails.

Request validation and response sanitisation for the LLM layer: enforces
message-length limits, blocks prompt-injection and raw-SQL payloads, and
redacts PII so it never reaches logs or downstream storage.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.config.logging import get_logger
from app.core.exceptions import EmbedHuntException

logger = get_logger(__name__)

MAX_MESSAGE_LENGTH = 50000

# Any single character repeated more than this many times is treated as an
# obfuscation attempt (unicode padding to smuggle instructions past filters).
_MAX_CHAR_REPEAT = 50


class GuardrailError(EmbedHuntException):
    def __init__(self, message: str):
        super().__init__(message, 400)


_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|prompts?)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+|the\s+|your\s+)?(previous|prior|above|system)\s+(instructions|prompts?)", re.IGNORECASE),
    re.compile(r"(reveal|show|print|repeat|leak)\s+(me\s+)?(your\s+|the\s+)?(system\s+prompt|instructions)", re.IGNORECASE),
    # "you are now" followed by any role redefinition.
    re.compile(r"you\s+are\s+now\s+\w+", re.IGNORECASE),
    re.compile(r"pretend\s+(to\s+be|you\s+are)", re.IGNORECASE),
    re.compile(r"override\s+your\s+(instructions|guardrails|rules)", re.IGNORECASE),
    # Fenced block immediately followed by a chat-role tag — an attempt to
    # inject a fake system/user/assistant turn.
    re.compile(r"`{3,}\s*(system|user|assistant)\b", re.IGNORECASE),
    re.compile(r"<\s*(system|assistant)\s*>", re.IGNORECASE),
    # A single character repeated > _MAX_CHAR_REPEAT times.
    re.compile(r"(.)\1{%d,}" % _MAX_CHAR_REPEAT, re.DOTALL),
]

_SQL_PATTERNS = [
    re.compile(r"\bdrop\s+table\b", re.IGNORECASE),
    re.compile(r";\s*drop\b", re.IGNORECASE),
    re.compile(r"\bunion\s+select\b", re.IGNORECASE),
    re.compile(r"\binsert\s+into\b", re.IGNORECASE),
    re.compile(r"\bdelete\s+from\b", re.IGNORECASE),
    re.compile(r"\bupdate\s+\w+\s+set\b", re.IGNORECASE),
    re.compile(r"\bselect\s+.+\s+from\s+\w+", re.IGNORECASE),
]

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")
_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _content_of(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


def validate_request(task: Any, messages: list, user_id: Optional[str] = None) -> None:
    """Validate an outbound LLM request.

    Raises :class:`GuardrailError` on any injection / SQL / length violation.
    Blocked requests are logged at WARNING with the ``user_id`` only — never the
    offending content, so we don't persist attacker-controlled payloads.
    """
    def _block(reason: str) -> None:
        logger.warning("guardrail_blocked", reason=reason, user_id=user_id or "unknown",
                       task=getattr(task, "value", str(task)))
        raise GuardrailError(f"blocked: {reason}")

    total = 0
    for message in messages:
        content = _content_of(message)
        length = len(content)
        total += length
        if length > MAX_MESSAGE_LENGTH:
            _block(f"message exceeds max length of {MAX_MESSAGE_LENGTH} chars")
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content):
                _block("potential prompt injection detected")
        for pattern in _SQL_PATTERNS:
            if pattern.search(content):
                _block("raw SQL detected in prompt")
    if total > MAX_MESSAGE_LENGTH:
        _block(f"combined messages exceed max length of {MAX_MESSAGE_LENGTH} chars")


def sanitize_response(content: str, user_id: Optional[str] = None) -> str:
    """Strip email / phone / Aadhaar / card PII from a model response.

    Logs at WARNING (with ``user_id`` only) when any PII is detected so leaks are
    observable without recording the sensitive value itself.
    """
    detected: list[str] = []
    cleaned = content

    if _EMAIL.search(cleaned):
        detected.append("email")
        cleaned = _EMAIL.sub("[redacted-email]", cleaned)
    if _AADHAAR.search(cleaned):
        detected.append("aadhaar")
        cleaned = _AADHAAR.sub("[redacted-aadhaar]", cleaned)
    if _CARD.search(cleaned):
        detected.append("card")
        cleaned = _CARD.sub("[redacted-card]", cleaned)
    if _PHONE.search(cleaned):
        detected.append("phone")
        cleaned = _PHONE.sub("[redacted-phone]", cleaned)

    if detected:
        logger.warning("pii_redacted", types=",".join(detected), user_id=user_id or "unknown")
    return cleaned


def redact_pii(text: str) -> str:
    return sanitize_response(text)
