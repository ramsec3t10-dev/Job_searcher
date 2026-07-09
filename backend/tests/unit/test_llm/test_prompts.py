"""Unit tests — prompt library integrity."""
import json

from app.llm.model_selector import TaskType
from app.llm.prompts import ALL_PROMPTS
from app.llm.prompts.base import PromptTemplate
from app.llm.token_manager import estimate_tokens

try:
    import jsonschema

    def _check_schema(schema: dict) -> None:
        jsonschema.Draft202012Validator.check_schema(schema)
except Exception:  # jsonschema not installed — fall back to structural checks
    def _check_schema(schema: dict) -> None:
        return None

_HAIKU_TASKS = {TaskType.EXTRACTION, TaskType.SUMMARIZATION}


def test_registry_is_complete():
    assert len(ALL_PROMPTS) == 18


def test_every_template_instantiates():
    for name, template in ALL_PROMPTS.items():
        assert isinstance(template, PromptTemplate), name
        assert isinstance(template.task_type, TaskType), name
        assert template.max_tokens > 0, name
        assert template.system_prompt.strip(), name
        assert template.user_template.strip(), name


def test_user_templates_render_with_matching_kwargs():
    for name, template in ALL_PROMPTS.items():
        placeholders = template.placeholders()
        assert placeholders, name  # every prompt takes at least one input
        kwargs = {key: "sample" for key in placeholders}
        rendered = template.render(**kwargs)
        assert isinstance(rendered, str) and rendered.strip(), name
        # No stray placeholders left unrendered.
        assert "{" not in rendered and "}" not in rendered, name


def test_output_schema_is_valid_json_schema():
    for name, template in ALL_PROMPTS.items():
        schema = template.expected_output_schema
        json.dumps(schema)  # must be JSON serializable
        assert isinstance(schema, dict), name
        assert schema.get("type") == "object", name
        assert isinstance(schema.get("properties"), dict), name
        assert schema["properties"], name
        _check_schema(schema)


def test_no_prompt_exceeds_3000_combined_tokens():
    for name, template in ALL_PROMPTS.items():
        combined = estimate_tokens(template.system_prompt) + estimate_tokens(template.user_template)
        assert combined < 3000, f"{name}: {combined} tokens"


def test_haiku_prompts_stay_under_2000_tokens():
    for name, template in ALL_PROMPTS.items():
        if template.task_type in _HAIKU_TASKS:
            combined = estimate_tokens(template.system_prompt) + estimate_tokens(template.user_template)
            assert combined < 2000, f"{name}: {combined} tokens"
