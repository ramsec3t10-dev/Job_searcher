"""Unit tests — LLM response parser."""
import pytest
from pydantic import BaseModel

from app.llm.response_parser import (
    ParseError,
    extract_field,
    parse_json,
    parse_structured,
)


def test_plain_json():
    assert parse_json('{"a": 1}') == {"a": 1}


def test_fenced_json_with_lang():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_fenced_json_without_lang():
    assert parse_json('```\n{"a": 2}\n```') == {"a": 2}


def test_json_embedded_in_prose():
    assert parse_json('Here you go:\n{"x": [1, 2]}\nHope that helps') == {"x": [1, 2]}


def test_invalid_json_raises_with_response():
    with pytest.raises(ParseError) as exc:
        parse_json("this is not json")
    assert exc.value.response == "this is not json"


class _Schema(BaseModel):
    name: str
    score: int


def test_parse_structured_valid():
    model = parse_structured('{"name": "ram", "score": 5}', _Schema)
    assert model.name == "ram"
    assert model.score == 5


def test_parse_structured_invalid_raises():
    with pytest.raises(ParseError):
        parse_structured('{"name": "ram"}', _Schema)


def test_extract_nested_field():
    assert extract_field('{"a": {"b": 7}}', "a.b") == 7


def test_extract_missing_field_raises():
    with pytest.raises(ParseError):
        extract_field('{"a": 1}', "b")
