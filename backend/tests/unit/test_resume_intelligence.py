"""Unit tests for Module 8 — resume intelligence (offline analyzer)."""
from app.ai.resume_intelligence import ResumeIntelligence, ResumeReport, get_resume_intelligence

STRONG_RESUME = """
Ram Kumar — Embedded Software Engineer
ram.kumar@example.com | +91 98765 43210

Summary
Embedded firmware engineer with 6 years building automotive systems.

Technical Skills:
C, C++, Python, FreeRTOS, CAN, SPI, I2C, ARM Cortex-M4, AUTOSAR, ISO 26262, JTAG, GDB

Experience
Bosch — Senior Firmware Engineer (2019 - Present)
- Developed FreeRTOS firmware that reduced boot time by 40%.
- Optimized CAN driver throughput improving latency by 25%.
- Integrated AUTOSAR BSW across 3 ECU platforms.

Education
B.E. Electronics, 2018
"""

WEAK_RESUME = "I am a hardworking team player looking for embedded work. I know some C."


def test_report_type_and_bounds():
    r = ResumeIntelligence().analyze(STRONG_RESUME)
    assert isinstance(r, ResumeReport)
    assert 0 <= r.ats_score <= 100


def test_strong_resume_scores_higher_than_weak():
    ex = ResumeIntelligence()
    assert ex.analyze(STRONG_RESUME).ats_score > ex.analyze(WEAK_RESUME).ats_score


def test_contact_and_sections_detected():
    r = ResumeIntelligence().analyze(STRONG_RESUME)
    assert r.has_email and r.has_phone
    assert {"summary", "experience", "education", "skills"} <= set(r.sections_found)


def test_action_verbs_and_quantification_counted():
    r = ResumeIntelligence().analyze(STRONG_RESUME)
    assert r.action_verb_count >= 3
    assert r.quantified_bullets >= 2


def test_cliches_flagged_in_weak_resume():
    r = ResumeIntelligence().analyze(WEAK_RESUME)
    assert any("player" in c or "hardworking" in c for c in r.cliches)
    assert r.suggestions  # weak resume yields suggestions


def test_missing_contact_yields_suggestions():
    r = ResumeIntelligence().analyze("Skills: C, CAN\nExperience\nDid stuff.")
    joined = " ".join(r.suggestions).lower()
    assert "email" in joined and "phone" in joined


def test_tailor_to_job_coverage():
    ex = ResumeIntelligence()
    job = "Looking for C, FreeRTOS, CAN, SPI, AUTOSAR, ISO 26262 firmware engineer."
    out = ex.tailor_to_job(STRONG_RESUME, job)
    assert 0.0 <= out["coverage"] <= 1.0
    assert out["coverage"] > 0.5
    assert isinstance(out["missing_skills"], list)


def test_tailor_identifies_missing():
    ex = ResumeIntelligence()
    job = "Need Rust, Zephyr, Ethernet, and MQTT for IoT firmware."
    out = ex.tailor_to_job("Skills: C, CAN, SPI", job)
    assert "rust" in out["missing_skills"] or "zephyr" in out["missing_skills"]
    assert out["coverage"] < 0.5


def test_singleton_accessor():
    assert get_resume_intelligence() is get_resume_intelligence()
