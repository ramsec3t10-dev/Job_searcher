"""Phase 5 — domain content (roadmaps, interview kits, career reasoner):
embedded regression (unchanged) + new-domain plausibility + no embedded jargon
leaking into other domains' outputs."""
import pytest

from app.agent.reasoner import reason_about_career
from app.interview.generator import generate_interview_kit_ai
from app.recommendation.engine import run_matching
from app.resume.normalizer import CandidateProfile
from app.roadmap.planner import generate_roadmap

_EMBEDDED_JARGON = ("rtos", "autosar", "firmware", "misra", "cortex", "can bus",
                    "freertos", "iso 26262", "bare metal", "memfault", "interrupt.memfault")


def _text_of_roadmap(r) -> str:
    parts = [r.summary]
    for t in r.tasks:
        parts.append(t.skill)
        parts += [res.get("title", "") + " " + res.get("url", "") for res in t.resources]
    return " ".join(parts).lower()


def _text_of_kit(k) -> str:
    parts = [k.preparation_summary, *k.checklist, *k.coding_topics]
    parts += [q.get("q", "") + " " + q.get("model_answer", "") for q in k.all_questions]
    return " ".join(parts).lower()


# ── 1. Embedded regression — roadmap unchanged ──────────────────────────────
class TestEmbeddedRoadmapRegression:
    def test_embedded_uses_original_tables(self):
        skills = ["can", "rtos", "autosar", "bootloader"]
        # domain_code=None (embedded/untagged) must use the original planner tables.
        r_none = generate_roadmap("u", skills, 60, "Firmware Engineer")
        r_emb = generate_roadmap("u", skills, 60, "Firmware Engineer", domain_code="embedded_engineering")
        # Both take the embedded path → identical output.
        assert [t.skill for t in r_none.tasks] == [t.skill for t in r_emb.tasks]
        assert r_none.total_hours == r_emb.total_hours
        # 'can' resolves to the embedded CAN resource, never a domain default.
        can = next(t for t in r_none.tasks if t.skill == "can")
        assert "csselectronics" in can.resources[0]["url"] or "can" in can.resources[0]["title"].lower()


# ── 2. New-domain roadmaps: progression order + real resources, no jargon ───
class TestNewDomainRoadmaps:
    def test_sales_roadmap(self):
        r = generate_roadmap("u", ["closing", "negotiation", "prospecting", "salesforce"],
                             55, "Account Executive", domain_code="sales")
        # Ordered by the sales progression: prospecting → salesforce → negotiation → closing.
        order = [t.skill for t in r.tasks]
        assert order.index("prospecting") < order.index("negotiation") < order.index("closing")
        assert not any(j in _text_of_roadmap(r) for j in _EMBEDDED_JARGON)

    def test_finance_roadmap(self):
        r = generate_roadmap("u", ["financial modeling", "excel", "audit"],
                             50, "Finance Manager", domain_code="finance")
        assert not any(j in _text_of_roadmap(r) for j in _EMBEDDED_JARGON)
        assert r.tasks  # produced real tasks

    def test_software_roadmap(self):
        r = generate_roadmap("u", ["kubernetes", "python", "system design"],
                             60, "Backend Engineer", domain_code="software_it")
        assert not any(j in _text_of_roadmap(r) for j in _EMBEDDED_JARGON)


# ── 3. Interview kits ───────────────────────────────────────────────────────
class TestInterviewKits:
    @pytest.mark.asyncio
    async def test_embedded_kit_technical_unchanged(self):
        kit = await generate_interview_kit_ai(
            "Firmware Engineer", "Bosch", ["c", "rtos", "can"], 75,
            db=None, user_id="u")  # domain_code None → technical path
        assert kit.coding_topics                       # embedded keeps coding topics
        assert kit.total_questions > 0

    @pytest.mark.asyncio
    async def test_sales_kit_no_coding_no_embedded_jargon(self):
        kit = await generate_interview_kit_ai(
            "Account Executive", "Acme", ["prospecting", "negotiation"], 70,
            db=None, user_id="u", domain_code="sales")
        assert kit.coding_topics == []                 # no coding for sales
        assert any(q["type"] == "role_play" for q in kit.all_questions)
        text = _text_of_kit(kit)
        assert not any(j in text for j in _EMBEDDED_JARGON), "embedded jargon leaked into sales kit"

    @pytest.mark.asyncio
    async def test_finance_kit_case_study_no_coding(self):
        kit = await generate_interview_kit_ai(
            "Finance Manager", "KPMG", ["financial modeling", "accounting"], 72,
            db=None, user_id="u", domain_code="finance")
        assert kit.coding_topics == []
        text = _text_of_kit(kit)
        assert "dcf" in text or "valuation" in text     # real finance content
        assert not any(j in text for j in _EMBEDDED_JARGON)


# ── 4. Career reasoner — embedded readiness unchanged; non-embedded sensible ─
class TestReasoner:
    def _embedded_profile(self):
        return CandidateProfile(
            name_hint="Emb", total_years_experience=6.0, is_embedded_engineer=True,
            embedded_domain_score=80,
            programming_languages=["c", "c++"], rtos_and_os=["rtos", "freertos"],
            protocols=["can", "spi", "i2c"], hardware_platforms=["arm"],
            automotive_safety=["autosar"], all_skills=["c", "c++", "rtos", "can", "arm", "autosar"],
        )

    def test_embedded_readiness_formula_unchanged(self):
        p = self._embedded_profile()
        result = run_matching(p, min_score=0, salary_min=0)
        insights = reason_about_career(p, result)
        best = result.jobs[0].match_score if result.jobs else 0
        assert insights.readiness_score == int(round(0.5 * p.embedded_domain_score + 0.5 * best))
        assert f"Profile domain score {p.embedded_domain_score}/100" in " ".join(insights.rationale)

    def test_non_embedded_readiness_is_market_match(self):
        p = CandidateProfile(name_hint="Sales", total_years_experience=4.0,
                             is_embedded_engineer=False, embedded_domain_score=0,
                             all_skills=["prospecting", "salesforce", "negotiation"])
        result = run_matching(p, min_score=0, salary_min=0)
        insights = reason_about_career(p, result)
        best = result.jobs[0].match_score if result.jobs else 0
        assert insights.readiness_score == best        # not halved by embedded_domain_score=0
        assert not any(j in " ".join(insights.rationale).lower() for j in ("embedded domain score",))
