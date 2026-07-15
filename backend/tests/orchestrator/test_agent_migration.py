"""EMBEDHUNT AI — Phase 4: agent → orchestrator migration regression tests.

Each migrated agent call site is driven with a mocked ``orchestrator.handle`` (no
Bedrock/Together) to prove (a) it routes through the orchestrator with the right
task name + ``user_id`` context, and (b) the parsed response shape the API layer
receives is unchanged.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.orchestrator.engine_base import EngineResult


def _mock_orchestrator(agent, text: str):
    orch = MagicMock()
    orch.handle = AsyncMock(return_value=EngineResult(
        text=text, engine_used="together:meta-llama/Llama-3.3-70B-Instruct-Turbo",
        confidence=0.9, cost_estimate_usd=0.0002, tokens_in=100, tokens_out=50))
    agent.orchestrator = orch
    return orch


# ── Call site #1: MatchingAgent.match → task "match_explanation" ─────────────
async def test_matching_agent_match_routes_through_orchestrator():
    from app.agents.matching_agent import MatchingAgent

    agent = MatchingAgent(db=None)
    job_match_json = (
        '{"score": 82, "reasoning": "Strong CAN/RTOS overlap; missing AUTOSAR.", '
        '"matched_skills": ["CAN", "RTOS"], "missing_skills": ["AUTOSAR"], '
        '"interview_probability": 70, "recommended_action": "apply"}'
    )
    orch = _mock_orchestrator(agent, job_match_json)

    twin = SimpleNamespace(skills=[{"name": "CAN"}], total_years_experience=5.0, current_role="FW Eng")
    job = {"title": "Embedded Engineer", "description": "CAN + RTOS", "required_skills": ["can", "rtos"]}
    result = await agent.match(twin, job, user_id="u1")

    # (a) routed through the orchestrator with the right task + user_id context.
    orch.handle.assert_awaited_once()
    args = orch.handle.await_args.args
    assert args[0] == "match_explanation"
    assert args[2]["user_id"] == "u1"
    assert args[1]["prompt"]  # rendered JOB_MATCH prompt forwarded

    # (b) response shape unchanged — a fully-parsed JobMatch.
    assert result.score == 82
    assert result.reasoning == "Strong CAN/RTOS overlap; missing AUTOSAR."
    assert result.interview_probability == 70
    assert result.missing_skills == ["AUTOSAR"]
    assert result.recommended_action == "apply"


async def test_matching_engine_enrichment_shape_after_migration():
    """The public matching_engine.match_ai contract is byte-identical: the base
    deterministic score is preserved and reasoning/explanation come from the
    orchestrator-routed agent."""
    from app.ai.embeddings import EmbeddingEngine
    from app.ai.matching_engine import MatchingEngine
    from app.ai.semantic_engine import SemanticMatchEngine
    from app.config.settings import settings
    from app.resume.normalizer import CandidateProfile

    settings_backup = settings.LLM_ENRICHMENT_ENABLED
    settings.LLM_ENRICHMENT_ENABLED = True
    try:
        eng = MatchingEngine(semantic=SemanticMatchEngine(engine=EmbeddingEngine(use_model=False)))
        profile = CandidateProfile(
            total_years_experience=6.0, is_embedded_engineer=True,
            programming_languages=["c"], protocols=["can"], rtos_and_os=["freertos"],
        )
        job = {"title": "Embedded Engineer", "description": "CAN FreeRTOS", "required_skills": "c,can,freertos"}
        base = eng.match(profile, job)

        # Patch the agent's orchestrator so the real agent code path runs, but no LLM.
        import app.agents.matching_agent as ma
        orig_init = ma.MatchingAgent.__init__

        def patched_init(self, db):
            orig_init(self, db)
            _mock_orchestrator(self, '{"score": 90, "reasoning": "Great fit.", "interview_probability": 80}')

        ma.MatchingAgent.__init__ = patched_init
        try:
            out = await eng.match_ai(profile, job, db=None, user_id="u1")
        finally:
            ma.MatchingAgent.__init__ = orig_init

        assert out.total_score == base.total_score          # deterministic base preserved
        assert out.reasoning == "Great fit."                # enriched from orchestrator
        assert out.interview_probability == 80
        assert out.explanation == "Great fit."
    finally:
        settings.LLM_ENRICHMENT_ENABLED = settings_backup
