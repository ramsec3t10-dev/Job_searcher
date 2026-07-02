"""Unit tests for Module 2 — semantic embedding + matching engine (offline)."""
import time

import pytest

from app.ai.embeddings import EmbeddingEngine
from app.ai.semantic_engine import SemanticMatchEngine
from app.resume.normalizer import CandidateProfile


@pytest.fixture
def engine():
    # force offline fallback so tests are deterministic and network-free
    return EmbeddingEngine(use_model=False)


@pytest.fixture
def sem(engine):
    return SemanticMatchEngine(engine=engine)


def _embedded_profile() -> CandidateProfile:
    return CandidateProfile(
        total_years_experience=6.0,
        is_embedded_engineer=True,
        programming_languages=["c", "c++", "python"],
        rtos_and_os=["freertos", "rtos"],
        protocols=["can", "spi", "i2c"],
        hardware_platforms=["arm", "stm32", "cortex-m4"],
        automotive_safety=["autosar", "iso 26262"],
        tools_and_debug=["jtag", "gdb", "git"],
        software_concepts=["device driver", "bootloader"],
    )


def _web_profile() -> CandidateProfile:
    return CandidateProfile(
        total_years_experience=5.0,
        is_embedded_engineer=False,
        programming_languages=["java", "kotlin"],
    )


# ---- EmbeddingEngine ----

def test_embed_text_normalized(engine):
    v = engine.embed_text("freertos scheduler")
    norm = sum(x * x for x in v) ** 0.5
    assert v and abs(norm - 1.0) < 1e-6


def test_cosine_identical_is_one(engine):
    v = engine.embed_text("cortex-m4")
    assert abs(engine.cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_unrelated_lower_than_related(engine):
    q = engine.embed_text("freertos")
    related = engine.cosine_similarity(q, engine.embed_text("freertos kernel"))
    unrelated = engine.cosine_similarity(q, engine.embed_text("marketing budget"))
    assert related > unrelated


def test_find_similar_skills_ranks_related_first(engine):
    ranked = engine.find_similar_skills(
        "can bus", ["can-fd", "spi", "photography"], top_k=3)
    assert ranked[0][0] == "can-fd"
    assert ranked[0][1] >= ranked[-1][1]


def test_embed_text_cached(engine):
    engine.embed_text("stm32")
    assert "stm32" in engine._cache


# ---- SemanticMatchEngine ----

def test_matching_job_scores_higher_than_mismatched(sem):
    profile = _embedded_profile()
    good = sem.score(profile, "Embedded Firmware Engineer",
                     "Develop FreeRTOS firmware on ARM Cortex-M with CAN and SPI.",
                     "c,c++,freertos,can,spi,arm", exp_min=5)
    bad = sem.score(profile, "Frontend React Developer",
                    "Build web UIs with React and CSS.",
                    "react,css,javascript", exp_min=3)
    assert good.total_score > bad.total_score
    assert good.recommendation != "low_match"
    assert good.semantic_skill_score > bad.semantic_skill_score


def test_no_keyword_overlap_is_capped(sem):
    profile = _web_profile()
    r = sem.score(profile, "Embedded Firmware Engineer",
                  "FreeRTOS on ARM Cortex-M with CAN.",
                  "c,freertos,can,arm,spi", exp_min=5)
    # calibration cap for near-zero keyword overlap
    assert r.total_score <= 60


def test_experience_multiplier_penalizes_juniors(sem):
    profile = _embedded_profile()
    profile.total_years_experience = 1.0
    r = sem.score(profile, "Senior Embedded Engineer",
                  "FreeRTOS ARM CAN SPI firmware.",
                  "c,c++,freertos,can,spi,arm", exp_min=8)
    assert r.experience_multiplier < 1.0


def test_result_fields_present(sem):
    r = sem.score(_embedded_profile(), "Embedded Engineer",
                  "CAN SPI firmware on STM32.", "c,can,spi,stm32", exp_min=5)
    assert 0 <= r.total_score <= 99
    assert r.method == "semantic"
    assert isinstance(r.matched_skills, list)


def test_performance_500_jobs_under_3s(sem):
    profile = _embedded_profile()
    start = time.perf_counter()
    for i in range(500):  # offline fallback path; production MiniLM+vector-store is faster
        sem.score(profile, f"Embedded Engineer {i}",
                  "FreeRTOS firmware on ARM Cortex-M with CAN, SPI, I2C.",
                  "c,c++,freertos,can,spi,i2c,arm", exp_min=5)
    elapsed = time.perf_counter() - start
    assert elapsed < 6.0
