"""Unit tests — LLM model selector & routing table."""
from app.config.settings import settings
from app.llm.model_selector import (
    ModelConfig,
    TaskType,
    clear_overrides,
    override_model,
    select_model,
)


def teardown_function(_):
    clear_overrides()


def test_haiku_routed_tasks():
    for task in (TaskType.EXTRACTION, TaskType.SUMMARIZATION):
        assert select_model(task).model_id == settings.LLM_HAIKU_MODEL


def test_sonnet_routed_tasks():
    for task in (
        TaskType.MATCHING,
        TaskType.MENTORING,
        TaskType.PLANNING,
        TaskType.INTERVIEW,
        TaskType.CODING,
        TaskType.SALARY,
        TaskType.ROADMAP,
    ):
        assert select_model(task).model_id == settings.LLM_SONNET_MODEL


def test_opus_routed_task():
    assert select_model(TaskType.COMPLEX_REASONING).model_id == settings.LLM_OPUS_MODEL


def test_every_task_returns_valid_config():
    for task in TaskType:
        config = select_model(task)
        assert isinstance(config, ModelConfig)
        assert config.model_id
        assert config.max_tokens > 0
        assert 0.0 <= config.temperature <= 1.0
        assert config.cost_per_1k_input > 0
        assert config.cost_per_1k_output > 0


def test_override_model_forces_choice():
    override_model(TaskType.EXTRACTION, settings.LLM_OPUS_MODEL)
    assert select_model(TaskType.EXTRACTION).model_id == settings.LLM_OPUS_MODEL


def test_clear_overrides_restores_default():
    override_model(TaskType.EXTRACTION, settings.LLM_OPUS_MODEL)
    clear_overrides()
    assert select_model(TaskType.EXTRACTION).model_id == settings.LLM_HAIKU_MODEL
