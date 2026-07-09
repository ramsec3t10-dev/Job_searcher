"""EMBEDHUNT AI — ContextBuilder tests."""
import json

import pytest

from app.llm.context_builder import ContextBuilder, MAX_CONTEXT_TOKENS
from app.llm.token_manager import estimate_tokens
from app.models.career_twin import CareerTwin
from app.models.memory import MemoryEntry


def _twin() -> CareerTwin:
    return CareerTwin(
        user_id="u1",
        full_name="Ram Kumar",
        current_role="Senior Embedded Engineer",
        current_company="Bosch",
        career_level="senior",
        total_years_experience=6.0,
        location="Bengaluru",
        current_salary_lpa=28.0,
        target_salary_lpa=40.0,
        learning_velocity=1.5,
        embedded_domain_score=82,
        skills=[
            {"name": "C", "category": "programming", "confidence": 0.9, "depth": "expert",
             "years_used": 6, "recency_score": 1.0, "last_used_year": 2026, "source": "resume"},
            {"name": "CAN", "category": "protocols", "confidence": 0.8, "depth": "working",
             "years_used": 5, "recency_score": 0.9, "last_used_year": 2026, "source": "resume"},
            {"name": "FreeRTOS", "category": "rtos", "confidence": 0.7, "depth": "working",
             "years_used": 4, "recency_score": 0.8, "last_used_year": 2025, "source": "resume"},
        ],
        strengths=["C", "debugging"],
        known_weaknesses=["system design"],
        interview_history=[{"company": "NXP", "score": 75}],
    )


def _tokens(payload: dict) -> int:
    return sum(
        estimate_tokens(v if isinstance(v, str) else json.dumps(v))
        for v in payload.values()
    )


def _job() -> dict:
    return {
        "title": "Embedded Software Engineer",
        "company": "NXP",
        "description": "Firmware development in C on ARM Cortex-M. " * 50,
        "required_skills": ["C", "CAN", "AUTOSAR", "Python"],
    }


@pytest.mark.parametrize("builder", [
    lambda: ContextBuilder.for_resume_analysis("resume text " * 2000, "job desc " * 500),
    lambda: ContextBuilder.for_job_matching(_twin(), _job()),
    lambda: ContextBuilder.for_career_mentor(
        _twin(),
        [MemoryEntry(user_id="u1", memory_type="conversation", summary="Wants to join NXP", importance_score=5, tags=["NXP"])],
        "How do I get to NXP?",
    ),
    lambda: ContextBuilder.for_interview(_twin(), _job(), "CAN"),
    lambda: ContextBuilder.for_roadmap(_twin(), _job(), 12),
    lambda: ContextBuilder.for_salary(_twin(), "NXP"),
])
def test_context_under_budget(builder):
    payload = builder()
    assert _tokens(payload) <= MAX_CONTEXT_TOKENS


def test_for_job_matching_field_names():
    payload = ContextBuilder.for_job_matching(_twin(), _job())
    assert set(payload.keys()) == {
        "candidate_summary", "skills", "experience_years", "current_role",
        "job_title", "job_description", "job_required_skills",
    }
    assert payload["job_title"] == "Embedded Software Engineer"
    assert "C" in payload["skills"]


def test_candidate_summary_bounded():
    payload = ContextBuilder.for_job_matching(_twin(), _job())
    assert len(payload["candidate_summary"]) <= 2000
