"""EMBEDHUNT AI — Phase 5 AI-enrichment tests.

Every migrated AI module gains an async ``*_ai`` enrichment path that wraps its
deterministic logic. For each module we assert the three contractually required
behaviours:

  1. ``LLM_ENRICHMENT_ENABLED = False``  -> deterministic behaviour, no AI fields.
  2. agent raises                        -> silent fallback to the deterministic result.
  3. agent returns a valid response      -> deterministic result enriched (never replaced).

The agents themselves are stubbed in their home module so no network/LLM/db is
touched. The deterministic base is always preserved.
"""
import pytest

from app.ai.embeddings import EmbeddingEngine
from app.ai.semantic_engine import SemanticMatchEngine
from app.agents.models import (
    InterviewQuestion,
    JobMatch,
    ParsedResume,
    Roadmap,
    RoadmapWeek,
    SalaryEstimate,
)
from app.config.settings import settings
from app.resume.normalizer import CandidateProfile

RESUME_TEXT = (
    "Senior Embedded Engineer. Technical Skills: C, C++, FreeRTOS, CAN, SPI, I2C. "
    "Experience: 6 years developing device drivers on ARM Cortex-M. "
    "Email: dev@example.com  Phone: +91 90000 11111"
)

JOB = {
    "id": "j1", "title": "Embedded Firmware Engineer", "company": "Bosch",
    "description": "FreeRTOS firmware on ARM Cortex-M with CAN, SPI, I2C, AUTOSAR.",
    "required_skills": "c,c++,freertos,can,spi,i2c,arm,autosar",
    "experience_min": 4, "salary_min_lpa": 20.0, "salary_max_lpa": 35.0,
}


def _profile() -> CandidateProfile:
    return CandidateProfile(
        total_years_experience=6.0,
        is_embedded_engineer=True,
        programming_languages=["c", "c++"],
        rtos_and_os=["freertos"],
        protocols=["can", "spi", "i2c"],
        hardware_platforms=["arm", "stm32", "cortex-m4"],
        automotive_safety=["autosar", "iso 26262"],
        tools_and_debug=["jtag", "gdb", "git"],
        software_concepts=["device driver"],
    )


# ── Stub agents (constructed inside each module via lazy import) ──────────────
class _FakeResumeAgent:
    def __init__(self, db):  # noqa: D401 - db intentionally ignored
        pass

    async def parse(self, resume_text, user_id):
        return ParsedResume(skills=["Rust Embedded", "Zephyr RTOS", "C"])


class _FailingResumeAgent:
    def __init__(self, db):
        pass

    async def parse(self, resume_text, user_id):
        raise RuntimeError("router unavailable")


class _FakeMatchingAgent:
    def __init__(self, db):
        pass

    async def match(self, twin, job, user_id):
        return JobMatch(score=80, reasoning="Strong protocol overlap.", interview_probability=72)


class _FailingMatchingAgent:
    def __init__(self, db):
        pass

    async def match(self, twin, job, user_id):
        raise RuntimeError("router unavailable")


class _FakeRoadmapAgent:
    def __init__(self, db):
        pass

    async def generate(self, user_id, target_job, hours_per_week):
        return Roadmap(weeks=[RoadmapWeek(
            number=1, skill="autosar", topic="AUTOSAR Classic",
            hours=8, activities=["Read RTE docs", "Build a SWC"], checkpoint="Quiz",
        )], total_weeks=1, career_path="Auto", summary="wk")


class _FailingRoadmapAgent:
    def __init__(self, db):
        pass

    async def generate(self, user_id, target_job, hours_per_week):
        raise RuntimeError("router unavailable")


class _FakeSalaryAgent:
    def __init__(self, db):
        pass

    async def estimate(self, user_id, target_company=None):
        return SalaryEstimate(
            estimated_min_lpa=30.0, estimated_max_lpa=45.0,
            negotiation_tips=["Anchor at 45 LPA", "Cite ARM + CAN premium"],
            market_reasoning="Your safety-critical stack commands a premium.",
        )


class _FailingSalaryAgent:
    def __init__(self, db):
        pass

    async def estimate(self, user_id, target_company=None):
        raise RuntimeError("router unavailable")


class _FakeInterviewAgent:
    def __init__(self, db):
        pass

    async def generate_questions(self, user_id, skill, company, difficulty, count=5):
        return [InterviewQuestion(
            text="Explain CAN arbitration at Bosch.", type="core",
            difficulty="hard", expected_answer_outline="Lower ID wins; dominant/recessive.",
        )]


class _FailingInterviewAgent:
    def __init__(self, db):
        pass

    async def generate_questions(self, user_id, skill, company, difficulty, count=5):
        raise RuntimeError("router unavailable")


# ── Module 1: resume_intelligence.analyze_ai ─────────────────────────────────
@pytest.mark.asyncio
async def test_resume_disabled_returns_deterministic(monkeypatch):
    from app.ai.resume_intelligence import ResumeIntelligence

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    ri = ResumeIntelligence()
    base = ri.analyze(RESUME_TEXT)
    out = await ri.analyze_ai(RESUME_TEXT, db=None, user_id="u1")
    assert out.top_skills == base.top_skills
    assert out.skill_count == base.skill_count


@pytest.mark.asyncio
async def test_resume_agent_error_falls_back(monkeypatch):
    from app.ai.resume_intelligence import ResumeIntelligence

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", _FailingResumeAgent)
    ri = ResumeIntelligence()
    base = ri.analyze(RESUME_TEXT)
    out = await ri.analyze_ai(RESUME_TEXT, db=None, user_id="u1")
    assert out.top_skills == base.top_skills


@pytest.mark.asyncio
async def test_resume_agent_success_enriches(monkeypatch):
    from app.ai.resume_intelligence import ResumeIntelligence

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", _FakeResumeAgent)
    ri = ResumeIntelligence()
    out = await ri.analyze_ai(RESUME_TEXT, db=None, user_id="u1")
    assert "Rust Embedded" in out.top_skills  # AI skill unioned in
    assert "Zephyr RTOS" in out.top_skills


# ── Module 6: skill_extractor.extract_ai ─────────────────────────────────────
@pytest.mark.asyncio
async def test_skill_disabled_returns_deterministic(monkeypatch):
    from app.ai.skill_extractor import SkillExtractor

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    se = SkillExtractor()
    base = se.extract(RESUME_TEXT)
    out = await se.extract_ai(RESUME_TEXT, db=None, user_id="u1")
    assert [s.name for s in out] == [s.name for s in base]


@pytest.mark.asyncio
async def test_skill_agent_error_falls_back(monkeypatch):
    from app.ai.skill_extractor import SkillExtractor

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", _FailingResumeAgent)
    se = SkillExtractor()
    base = se.extract(RESUME_TEXT)
    out = await se.extract_ai(RESUME_TEXT, db=None, user_id="u1")
    assert [s.name for s in out] == [s.name for s in base]


@pytest.mark.asyncio
async def test_skill_agent_success_unions_new_skills(monkeypatch):
    from app.ai.skill_extractor import SkillExtractor

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.resume_agent.ResumeAgent", _FakeResumeAgent)
    se = SkillExtractor()
    out = await se.extract_ai(RESUME_TEXT, db=None, user_id="u1")
    names = {s.name for s in out}
    assert "rust embedded" in names or "zephyr rtos" in names
    ai_added = [s for s in out if s.evidence == ["ai_inferred"]]
    assert ai_added and all(s.mentions == 0 for s in ai_added)


# ── Module 4: matching_engine.match_ai ───────────────────────────────────────
def _engine():
    sem = SemanticMatchEngine(engine=EmbeddingEngine(use_model=False))
    from app.ai.matching_engine import MatchingEngine
    return MatchingEngine(semantic=sem)


@pytest.mark.asyncio
async def test_match_disabled_returns_deterministic(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    eng = _engine()
    base = eng.match(_profile(), JOB)
    out = await eng.match_ai(_profile(), JOB, db=None, user_id="u1")
    assert out.total_score == base.total_score
    assert out.reasoning == "" and out.interview_probability == 0


@pytest.mark.asyncio
async def test_match_agent_error_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.matching_agent.MatchingAgent", _FailingMatchingAgent)
    eng = _engine()
    base = eng.match(_profile(), JOB)
    out = await eng.match_ai(_profile(), JOB, db=None, user_id="u1")
    assert out.total_score == base.total_score
    assert out.reasoning == ""


@pytest.mark.asyncio
async def test_match_agent_success_enriches(monkeypatch):
    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.matching_agent.MatchingAgent", _FakeMatchingAgent)
    eng = _engine()
    base = eng.match(_profile(), JOB)
    out = await eng.match_ai(_profile(), JOB, db=None, user_id="u1")
    assert out.total_score == base.total_score  # base score never changed
    assert out.reasoning == "Strong protocol overlap."
    assert out.interview_probability == 72
    assert out.explanation == "Strong protocol overlap."


# ── Module 3: adaptive_roadmap.build_ai ──────────────────────────────────────
def _build_kwargs():
    return dict(
        skill_confidence={}, target_skills=["autosar", "freertos"],
        current_score=40, job_title="Auto", hours_per_week=10,
    )


@pytest.mark.asyncio
async def test_roadmap_disabled_returns_deterministic(monkeypatch):
    from app.ai.adaptive_roadmap import AdaptiveRoadmapEngine

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    eng = AdaptiveRoadmapEngine()
    base = eng.build(**_build_kwargs())
    out = await eng.build_ai(**_build_kwargs(), db=None, user_id="u1")
    assert out.ai_weekly_plan == []
    assert out.projected_score == base.projected_score


@pytest.mark.asyncio
async def test_roadmap_agent_error_falls_back(monkeypatch):
    from app.ai.adaptive_roadmap import AdaptiveRoadmapEngine

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.roadmap_agent.RoadmapAgent", _FailingRoadmapAgent)
    eng = AdaptiveRoadmapEngine()
    base = eng.build(**_build_kwargs())
    out = await eng.build_ai(**_build_kwargs(), db=None, user_id="u1")
    assert out.ai_weekly_plan == []
    assert out.projected_score == base.projected_score


@pytest.mark.asyncio
async def test_roadmap_agent_success_enriches(monkeypatch):
    from app.ai.adaptive_roadmap import AdaptiveRoadmapEngine

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.roadmap_agent.RoadmapAgent", _FakeRoadmapAgent)
    eng = AdaptiveRoadmapEngine()
    base = eng.build(**_build_kwargs())
    out = await eng.build_ai(**_build_kwargs(), db=None, user_id="u1")
    assert out.ai_weekly_plan  # AI weeks attached
    assert out.ai_weekly_plan[0]["skill"] == "autosar"
    assert out.projected_score == base.projected_score  # projection stays deterministic


# ── Module 12: salary_intelligence.compute_ai ────────────────────────────────
def _salary_kwargs():
    return dict(
        years_experience=6.0, skill_names=["c", "can", "autosar"],
        domains=["automotive"], locations=["bangalore"],
        current_salary_lpa=22.0, dream_companies=["bosch"],
    )


@pytest.mark.asyncio
async def test_salary_disabled_returns_deterministic(monkeypatch):
    from app.ai.salary_intelligence import SalaryIntelligenceEngine

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    eng = SalaryIntelligenceEngine()
    base = eng.compute(**_salary_kwargs())
    out = await eng.compute_ai(**_salary_kwargs(), db=None, user_id="u1")
    assert out.negotiation_tips == []
    assert out.market_reasoning == ""
    assert out.estimated_market_min == base.estimated_market_min


@pytest.mark.asyncio
async def test_salary_agent_error_falls_back(monkeypatch):
    from app.ai.salary_intelligence import SalaryIntelligenceEngine

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.salary_agent.SalaryAgent", _FailingSalaryAgent)
    eng = SalaryIntelligenceEngine()
    base = eng.compute(**_salary_kwargs())
    out = await eng.compute_ai(**_salary_kwargs(), db=None, user_id="u1")
    assert out.negotiation_tips == []
    assert out.estimated_market_max == base.estimated_market_max


@pytest.mark.asyncio
async def test_salary_agent_success_enriches(monkeypatch):
    from app.ai.salary_intelligence import SalaryIntelligenceEngine

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.salary_agent.SalaryAgent", _FakeSalaryAgent)
    eng = SalaryIntelligenceEngine()
    base = eng.compute(**_salary_kwargs())
    out = await eng.compute_ai(**_salary_kwargs(), db=None, user_id="u1")
    assert out.estimated_market_min == base.estimated_market_min  # base numbers unchanged
    assert "Anchor at 45 LPA" in out.negotiation_tips
    assert out.market_reasoning.startswith("Your safety-critical")


# ── Module: interview.generator.generate_interview_kit_ai ────────────────────
@pytest.mark.asyncio
async def test_interview_disabled_returns_static(monkeypatch):
    from app.interview.generator import generate_interview_kit, generate_interview_kit_ai

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    base = generate_interview_kit("Firmware Engineer", "Bosch", ["c", "can"], 70)
    out = await generate_interview_kit_ai(
        "Firmware Engineer", "Bosch", ["c", "can"], 70, db=None, user_id="u1",
    )
    assert out.total_questions == base.total_questions
    assert all(q.get("source") != "ai" for q in out.all_questions)


@pytest.mark.asyncio
async def test_interview_agent_error_falls_back(monkeypatch):
    from app.interview.generator import generate_interview_kit, generate_interview_kit_ai

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.interview_agent.InterviewAgent", _FailingInterviewAgent)
    base = generate_interview_kit("Firmware Engineer", "Bosch", ["c", "can"], 70)
    out = await generate_interview_kit_ai(
        "Firmware Engineer", "Bosch", ["c", "can"], 70, db=None, user_id="u1",
    )
    assert out.total_questions == base.total_questions


@pytest.mark.asyncio
async def test_interview_agent_success_prepends_ai(monkeypatch):
    from app.interview.generator import generate_interview_kit_ai

    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr("app.agents.interview_agent.InterviewAgent", _FakeInterviewAgent)
    out = await generate_interview_kit_ai(
        "Firmware Engineer", "Bosch", ["c", "can"], 70, db=None, user_id="u1",
    )
    assert out.all_questions[0]["source"] == "ai"  # AI questions come first
    assert out.all_questions[0]["q"].startswith("Explain CAN arbitration")
