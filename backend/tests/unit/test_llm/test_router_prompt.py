"""Unit tests — AIRouter running PromptTemplates end-to-end (stubbed Bedrock)."""
from app.llm.cache import SemanticCache
from app.llm.model_selector import TaskType
from app.llm.prompts import RESUME_PARSER
from app.llm.router import AIRouter


class _StubBedrock:
    def __init__(self):
        self.calls = []

    async def invoke_model(self,model_id,messages,system=None,max_tokens=1024,temperature=0.4,timeout=None,task=None):
        self.calls.append({ "model": model_id, "messages": messages, "system": system, "task": task, })
        return {
            "content": '{"skills": ["c", "freertos"], "total_years": 6}',
            "input_tokens": 120,
            "output_tokens": 30,
            "latency_ms": 8.0,
            "model": model_id,
        }


def _router():
    return AIRouter(bedrock_client=_StubBedrock(), cache=SemanticCache(force_memory=True))


async def test_run_prompt_renders_and_routes():
    router = _router()
    response = await router.run_prompt(RESUME_PARSER, resume_text="Firmware engineer, 6 years C/FreeRTOS")
    assert response.model_used  # a model was selected for the task
    assert response.task_type == TaskType.EXTRACTION
    assert response.input_tokens == 120 and response.output_tokens == 30
    assert response.cost_usd > 0
    # The rendered user message must carry the substituted resume text.
    sent = router.bedrock.calls[0]
    assert "Firmware engineer" in sent["messages"][0]["content"]
    assert sent["system"] == RESUME_PARSER.system_prompt


async def test_run_prompt_output_parses_against_contract():
    from app.llm.response_parser import parse_json

    router = _router()
    response = await router.run_prompt(RESUME_PARSER, resume_text="anything")
    data = parse_json(response.content)
    assert data["skills"] == ["c", "freertos"]
    assert data["total_years"] == 6
