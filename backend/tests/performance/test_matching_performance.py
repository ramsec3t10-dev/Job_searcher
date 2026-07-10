"""EMBEDHUNT AI — matching engine performance test.

Ranks 500 jobs against one candidate profile and asserts it completes well under
3 seconds. The matching engine is pure compute (no LLM), so Bedrock is never
called here; this guards against accidental O(n^2) or per-job network regressions.
"""
import time

from app.recommendation.engine import run_matching
from app.resume.normalizer import CandidateProfile


def _profile() -> CandidateProfile:
    return CandidateProfile(
        total_years_experience=6.0,
        current_role="Embedded Engineer",
        is_embedded_engineer=True,
        programming_languages=["C", "C++"],
        rtos_and_os=["FreeRTOS", "Linux kernel"],
        protocols=["CAN", "SPI", "I2C", "UART", "Ethernet"],
        hardware_platforms=["ARM Cortex-M", "STM32"],
        automotive_safety=["ISO 26262", "AUTOSAR"],
        tools_and_debug=["JTAG", "CANoe"],
        software_concepts=["device driver", "bootloader"],
        all_skills=["C", "C++", "FreeRTOS", "CAN", "SPI", "I2C", "ARM", "AUTOSAR", "ISO 26262"],
        skill_count=9,
        embedded_domain_score=85,
    )


def _corpus(n: int = 500) -> list[dict]:
    skills = "C,C++,ARM,RTOS,FreeRTOS,CAN,LIN,SPI,I2C,UART,Ethernet,AUTOSAR,ISO 26262,device driver,bootloader"
    jobs = []
    for i in range(n):
        jobs.append({
            "id": f"perf-{i:04d}",
            "title": "Embedded Software Engineer",
            "company": f"Company {i}",
            "company_tier": "tier1_semiconductor",
            "location": "Bangalore, India",
            "source_portal": "perf",
            "source_url": "https://example.com",
            "apply_url": "https://example.com",
            "description": "ARM Cortex-M firmware, RTOS, C/C++, CAN, SPI, I2C, device drivers.",
            "required_skills": skills,
            "experience_min": 2,
            "experience_max": 8,
            "salary_min_lpa": 18.0,
            "salary_max_lpa": 40.0,
        })
    return jobs


def test_match_500_jobs_under_three_seconds():
    profile = _profile()
    corpus = _corpus(500)

    start = time.perf_counter()
    result = run_matching(profile, min_score=0, corpus=corpus)
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0, f"matching 500 jobs took {elapsed:.2f}s"
    assert len(result.jobs) > 0
