"""EMBEDHUNT AI — LLM Response Parsing.

Robustly extracts structured data from raw model output. Every failure raises
a ParseError that carries the original response for debugging.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from app.core.exceptions import ParseError as _BaseParseError


class ParseError(_BaseParseError):
    def __init__(self, message: str, response: str = ""):
        super().__init__(message)
        self.response = response


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t.strip())
    return t.strip()


def _extract_json_blob(text: str) -> str:
    t = _strip_fences(text)
    candidates = [i for i in (t.find("{"), t.find("[")) if i != -1]
    if not candidates:
        return t
    start = min(candidates)
    closer = "}" if t[start] == "{" else "]"
    end = t.rfind(closer)
    if end == -1 or end < start:
        return t[start:]
    return t[start:end + 1]


def parse_json(response: str) -> dict:
    blob = _extract_json_blob(response)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON: {exc}", response) from exc
    if not isinstance(data, (dict, list)):
        raise ParseError("Parsed JSON is not an object or array", response)
    return data


def parse_structured(response: str, schema: type[BaseModel]) -> BaseModel:
    data = parse_json(response)
    try:
        return schema.model_validate(data)
    except Exception as exc:
        raise ParseError(f"Schema validation failed: {exc}", response) from exc


def extract_field(response: str, field: str) -> Any:
    data = parse_json(response)
    current: Any = data
    for part in field.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ParseError(f"Field '{field}' not found in response", response)
    return current
