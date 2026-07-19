"""Phase 3 — CRITICAL regression: the config-driven matcher must reproduce the
pre-Phase-3 embedded scoring EXACTLY, both with the default config and with a
config whose weights come from the Phase-1 SkillCategory rows.

If this test ever fails, embedded matching has regressed — stop and fix before
anything else.
"""
import pytest

from app.recommendation import matcher as new_matcher
from app.recommendation.engine import _job_corpus
from app.recommendation.matcher import CategoryConfig, DomainScoringConfig
from app.resume.normalizer import CandidateProfile
from app.domains.catalog import EMBEDDED_CATEGORIES
from tests.unit import _legacy_matcher_baseline as legacy


# ── Fixed candidate fixtures spanning strong / mid / weak embedded profiles ──
def _profiles() -> list[CandidateProfile]:
    strong = CandidateProfile(
        name_hint="Strong", total_years_experience=6.0, is_embedded_engineer=True,
        programming_languages=["c", "c++", "python"], rtos_and_os=["rtos", "freertos", "linux kernel"],
        protocols=["can", "spi", "i2c", "uart", "ethernet"], hardware_platforms=["arm", "arm cortex-m", "stm32"],
        automotive_safety=["autosar", "iso 26262", "asil", "misra c"], tools_and_debug=["gdb", "jtag"],
        software_concepts=["device driver", "bootloader", "bare metal"],
        all_skills=["c", "c++", "python", "rtos", "freertos", "linux kernel", "can", "spi", "i2c",
                    "uart", "ethernet", "arm", "arm cortex-m", "stm32", "autosar", "iso 26262",
                    "asil", "misra c", "gdb", "jtag", "device driver", "bootloader", "bare metal"],
    )
    mid = CandidateProfile(
        name_hint="Mid", total_years_experience=2.5, is_embedded_engineer=True,
        programming_languages=["c", "python"], rtos_and_os=["freertos"],
        protocols=["spi", "i2c", "uart"], hardware_platforms=["arm", "esp32"],
        automotive_safety=[], tools_and_debug=["gdb"], software_concepts=["device driver"],
        all_skills=["c", "python", "freertos", "spi", "i2c", "uart", "arm", "esp32", "gdb", "device driver"],
    )
    weak = CandidateProfile(
        name_hint="Weak", total_years_experience=0.5, is_embedded_engineer=False,
        programming_languages=["python"], rtos_and_os=[], protocols=[], hardware_platforms=["arduino"],
        automotive_safety=[], tools_and_debug=[], software_concepts=[],
        all_skills=["python", "arduino", "react", "typescript"],
    )
    empty = CandidateProfile(name_hint="Empty")
    return [strong, mid, weak, empty]


def _assert_identical(a, b, label):
    assert a.total_score == b.total_score, f"{label}: total {a.total_score} != {b.total_score}"
    assert a.base_score == b.base_score, f"{label}: base"
    assert a.experience_bonus == b.experience_bonus, f"{label}: exp_bonus"
    assert a.domain_bonus == b.domain_bonus, f"{label}: domain_bonus"
    assert a.matched_skills == b.matched_skills, f"{label}: matched"
    assert a.missing_skills == b.missing_skills, f"{label}: missing"
    assert a.explanation == b.explanation, f"{label}: explanation"
    assert a.recommendation == b.recommendation, f"{label}: recommendation"
    assert len(a.category_scores) == len(b.category_scores), f"{label}: n_cats"
    for ca, cb in zip(a.category_scores, b.category_scores):
        assert (ca.category, ca.weight, ca.raw_score, ca.weighted_score) == \
               (cb.category, cb.weight, cb.raw_score, cb.weighted_score), f"{label}: cat {ca.category}"


def _db_weighted_embedded_config() -> DomainScoringConfig:
    """Embedded config whose WEIGHTS come from the Phase-1 SkillCategory seed
    rows (EMBEDDED_CATEGORIES) — proves DB-sourced weights reproduce scoring."""
    db_weights = {code: w for code, _n, w in EMBEDDED_CATEGORIES}
    cats = tuple(
        CategoryConfig(code, db_weights[code],
                       frozenset(new_matcher.CATEGORY_SETS[code]),
                       new_matcher.PROFILE_ATTRS[code])
        for code in new_matcher.WEIGHTS
    )
    return DomainScoringConfig("embedded_engineering", cats, embedded_bonus=True)


@pytest.mark.parametrize("job", _job_corpus())
def test_config_none_matches_legacy(job):
    for profile in _profiles():
        old = legacy.compute_match(profile, job.get("title", ""), job.get("description"),
                                   job.get("required_skills"), job.get("experience_min"), job.get("experience_max"))
        new = new_matcher.compute_match(profile, job.get("title", ""), job.get("description"),
                                        job.get("required_skills"), job.get("experience_min"), job.get("experience_max"))
        _assert_identical(old, new, f"{job['id']}/{profile.name_hint}")


@pytest.mark.parametrize("job", _job_corpus())
def test_db_weighted_config_matches_legacy(job):
    cfg = _db_weighted_embedded_config()
    for profile in _profiles():
        old = legacy.compute_match(profile, job.get("title", ""), job.get("description"),
                                   job.get("required_skills"), job.get("experience_min"), job.get("experience_max"))
        new = new_matcher.compute_match(profile, job.get("title", ""), job.get("description"),
                                        job.get("required_skills"), job.get("experience_min"), job.get("experience_max"),
                                        config=cfg)
        _assert_identical(old, new, f"DBW {job['id']}/{profile.name_hint}")


def test_weights_equal_hardcoded():
    # The Phase-1 seed rows must equal the in-code embedded weights exactly.
    assert {code: w for code, _n, w in EMBEDDED_CATEGORIES} == new_matcher.WEIGHTS
