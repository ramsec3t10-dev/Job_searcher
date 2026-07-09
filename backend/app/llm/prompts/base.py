"""EMBEDHUNT AI — Prompt template primitives.

Defines the typed PromptTemplate used across the prompt library plus small
helpers for declaring minimal JSON Schemas for expected model output.
"""
from __future__ import annotations

import string
from dataclasses import dataclass

from app.llm.model_selector import TaskType

STR: dict = {"type": "string"}
INT: dict = {"type": "integer"}
NUM: dict = {"type": "number"}
BOOL: dict = {"type": "boolean"}


def arr(items: dict | None = None) -> dict:
    return {"type": "array", "items": items if items is not None else {}}


def obj(required: list[str] | None = None, **props: dict) -> dict:
    schema: dict = {"type": "object", "properties": props, "additionalProperties": True}
    if required:
        schema["required"] = list(required)
    return schema


@dataclass(frozen=True)
class PromptTemplate:
    system_prompt: str
    user_template: str
    task_type: TaskType
    max_tokens: int
    expected_output_schema: dict

    def render(self, **kwargs) -> str:
        return self.user_template.format(**kwargs)

    def placeholders(self) -> set[str]:
        return {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(self.user_template)
            if field_name
        }
