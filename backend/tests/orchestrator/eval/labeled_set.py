"""Labeled examples for the confidence-heuristic eval (Phase 6).

Each row is a realistic model output for an EMBEDHUNT task, hand-labeled by
**independent quality judgement** (not by the heuristic): should this answer have
been *served* by the cheap open model, or *escalated* to Claude?

    expect_escalate = True  → a human would reject this and want Claude
    expect_escalate = False → good enough to serve from the open model

The eval measures how often the Phase-3 confidence heuristic AGREES. A couple of
rows are deliberate edge cases where a shape-only heuristic diverges from quality
judgement (e.g. valid-but-empty JSON) so the report surfaces its known gaps.
"""

_LONG_TRUNCATED = (
    "Bosch develops automotive embedded systems including engine control units, "
    "ABS, airbag controllers, radar sensors and AUTOSAR-based software platforms "
    "for powertrain and chassis domains used by major OEMs worldwide across"
)

# task, output, finish_reason, expect_escalate, note
LABELED: list[dict] = [
    # ── structured extraction: valid JSON should serve ─────────────────────
    {"task": "skill_extraction", "output": '{"skills":["CAN","RTOS","AUTOSAR"]}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},
    {"task": "skill_extraction", "output": '```json\n{"skills":["SPI","I2C"]}\n```', "finish_reason": "stop", "expect_escalate": False, "note": "fenced JSON"},
    {"task": "skill_extraction", "output": "I could not extract skills from this resume.", "finish_reason": "stop", "expect_escalate": True, "note": "refusal, not JSON"},
    {"task": "skill_extraction", "output": "", "finish_reason": "stop", "expect_escalate": True, "note": "empty"},
    {"task": "resume_parsing", "output": '{"name":"[REDACTED]","skills":["c","freertos"],"years":6}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},
    {"task": "resume_parsing", "output": "Sure! Here is the parsed resume in a readable format:", "finish_reason": "stop", "expect_escalate": True, "note": "prose, not JSON"},
    {"task": "job_description_extraction", "output": '{"title":"Firmware Engineer","required":["can","rtos"]}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},
    {"task": "job_description_extraction", "output": "{}", "finish_reason": "stop", "expect_escalate": True, "note": "empty JSON — nothing extracted"},
    {"task": "match_explanation", "output": '{"score":82,"reasoning":"Strong CAN/RTOS overlap.","missing_skills":["AUTOSAR"]}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},
    {"task": "match_explanation", "output": "The candidate is a decent match overall.", "finish_reason": "stop", "expect_escalate": True, "note": "prose, not JSON"},
    {"task": "roadmap_draft", "output": '{"weeks":[{"n":1,"skill":"autosar"}],"total_weeks":8}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},
    {"task": "roadmap_draft", "output": "Here is a plan: week 1 learn AUTOSAR basics, then...", "finish_reason": "stop", "expect_escalate": True, "note": "prose, not JSON"},
    {"task": "skill_extraction", "output": '{"skills":["MISRA C","ISO 26262","Tessy"]}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},
    {"task": "resume_parsing", "output": '{"skills":["c","c++","freertos","can","spi"],"years":8,"summary":"embedded eng"}', "finish_reason": "stop", "expect_escalate": False, "note": "clean JSON"},

    # ── freeform summaries: coherent should serve ──────────────────────────
    {"task": "company_summary", "output": "Bosch is a tier-1 automotive supplier specializing in embedded ECUs, AUTOSAR software and functional safety for powertrain and ADAS systems.", "finish_reason": "stop", "expect_escalate": False, "note": "good summary"},
    {"task": "company_summary", "output": "Acme is good.", "finish_reason": "stop", "expect_escalate": True, "note": "too short"},
    {"task": "company_summary", "output": "buy buy buy buy buy buy buy buy buy buy buy buy", "finish_reason": "stop", "expect_escalate": True, "note": "repetition loop"},
    {"task": "company_summary", "output": _LONG_TRUNCATED, "finish_reason": "length", "expect_escalate": True, "note": "truncated mid-sentence"},
    {"task": "company_summary", "output": "NVIDIA designs GPUs, Tegra SoCs and the DRIVE platform for autonomous vehicles, with deep embedded and CUDA software stacks used across automotive and robotics.", "finish_reason": "stop", "expect_escalate": False, "note": "good summary"},
    {"task": "company_summary", "output": "Qualcomm designs Snapdragon SoCs, modems and automotive platforms; strong in embedded DSP, RF and low-power firmware.", "finish_reason": "stop", "expect_escalate": False, "note": "good summary"},
    {"task": "company_summary", "output": "error error error error error error error error error error", "finish_reason": "stop", "expect_escalate": True, "note": "degenerate repetition"},
    {"task": "company_summary", "output": "A leading company.", "finish_reason": "stop", "expect_escalate": True, "note": "too short / low value"},

    # ── deliberate edge cases: shape-heuristic vs quality judgement ─────────
    {"task": "skill_extraction", "output": '{"skills":[]}', "finish_reason": "stop", "expect_escalate": True, "note": "EDGE: valid JSON but empty extraction (heuristic will under-escalate)"},
    {"task": "company_summary", "output": "This is a technology company that makes many different products for various global industries and markets today.", "finish_reason": "stop", "expect_escalate": True, "note": "EDGE: fluent but generic/low-value (heuristic will under-escalate)"},
]
