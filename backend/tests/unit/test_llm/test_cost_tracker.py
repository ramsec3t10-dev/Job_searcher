"""Unit tests — LLM cost tracker & budget logic."""
from app.llm.cost_tracker import AIUsageLog, CostTracker
from app.llm.model_selector import TaskType, select_model
from app.llm.router import AIResponse, AIRouter


def test_cost_calculation_matches_rates():
    config = select_model(TaskType.MATCHING)
    cost = AIRouter._cost(config, 1000, 1000)
    assert cost == round(config.cost_per_1k_input + config.cost_per_1k_output, 6)


def test_zero_tokens_cost_zero():
    config = select_model(TaskType.EXTRACTION)
    assert AIRouter._cost(config, 0, 0) == 0.0


def test_usage_log_row_fields():
    response = AIResponse(
        content="x",
        model_used="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
        latency_ms=20.0,
        cached=False,
        task_type=TaskType.MATCHING,
    )
    row = AIUsageLog(
        user_id="u",
        task_type=response.task_type.value,
        model=response.model_used,
        tokens_in=response.input_tokens,
        tokens_out=response.output_tokens,
        cost_usd=response.cost_usd,
        latency_ms=response.latency_ms,
        cached=response.cached,
    )
    assert row.tokens_in == 100
    assert row.tokens_out == 50
    assert row.model == "claude-sonnet-4-6"
    assert row.task_type == "matching"


class _StubTracker(CostTracker):
    def __init__(self, spend: float):
        super().__init__()
        self._spend = spend

    async def get_user_cost(self, user_id, period_days=30, db=None):
        return self._spend


async def test_over_budget_true_when_above_limit():
    assert await _StubTracker(3.0).is_over_budget("u", 2.0) is True


async def test_over_budget_false_when_below_limit():
    assert await _StubTracker(0.5).is_over_budget("u", 2.0) is False


async def test_over_budget_uses_settings_default_limit():
    assert await _StubTracker(2.5).is_over_budget("u") is True
