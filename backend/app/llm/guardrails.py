"""EMBEDHUNT AI — LLM Guardrails.

Request validation and response sanitisation for the LLM layer: enforces
message-length limits, blocks prompt-injection and raw-SQL payloads, and
redacts PII so it never reaches logs or downstream storage.
"""
from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import EmbedHuntException

MAX_MESSAGE_LENGTH = 50000


class GuardrailError(EmbedHuntException):
    def __init__(self, message: str):
        super().__init__(message, 400)


_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|prompts?)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+|the\s+)?(previous|prior|above|system)\s+(instructions|prompts?)", re.IGNORECASE),
    re.compile(r"(reveal|show|print|repeat|leak)\s+(me\s+)?(your\s+|the\s+)?(system\s+prompt|instructions)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|acting)", re.IGNORECASE),
    re.compile(r"pretend\s+(to\s+be|you\s+are)", re.IGNORECASE),
    re.compile(r"override\s+your\s+(instructions|guardrails|rules)", re.IGNORECASE),
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
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _content_of(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)


def validate_request(task: Any, messages: list) -> None:
    total = 0
    for message in messages:
        content = _content_of(message)
        length = len(content)
        total += length
        if length > MAX_MESSAGE_LENGTH:
            raise GuardrailError(f"message exceeds max length of {MAX_MESSAGE_LENGTH} chars")
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content):
                raise GuardrailError("blocked: potential prompt injection detected")
        for pattern in _SQL_PATTERNS:
            if pattern.search(content):
                raise GuardrailError("blocked: raw SQL detected in prompt")
    if total > MAX_MESSAGE_LENGTH:
        raise GuardrailError(f"combined messages exceed max length of {MAX_MESSAGE_LENGTH} chars")


def sanitize_response(content: str) -> str:
    cleaned = _EMAIL.sub("[redacted-email]", content)
    cleaned = _CARD.sub("[redacted-card]", cleaned)
    cleaned = _PHONE.sub("[redacted-phone]", cleaned)
    return cleaned


def redact_pii(text: str) -> str:
    return sanitize_response(text)
