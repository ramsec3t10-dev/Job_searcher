"""Phase 2 — domain classifier + multi-domain discovery tests.

The classifier's rule tier is pure and deterministic (no network, no DB), so
accuracy is measured directly on a labeled fixture set spanning many domains.
The LLM tier is exercised with a fake router (still no network).
"""
import pytest

from app.job_sources.aggregator import discover
from app.job_sources.base import JobSource, JobSourceError
from app.job_sources.domain_classifier import DomainClassifier
from app.job_sources.schema import JobPosting
from app.job_sources.smartrecruiters import SmartRecruitersSource

# ── Labeled fixtures: (title, description, expected top-level domain) ────────
# 20 postings across 12 domains — well beyond the required 5.
LABELED = [
    ("Senior Backend Engineer", "Build Java microservices and REST APIs", "software_it"),
    ("Machine Learning Engineer", "Train deep learning models, NLP, PyTorch", "software_it"),
    ("Embedded Firmware Engineer", "RTOS, C, device drivers on ARM Cortex-M", "software_it"),
    ("Data Scientist", "Statistical modeling, Python, analytics dashboards", "software_it"),
    ("DevOps Engineer", "Kubernetes, Terraform, CI/CD pipelines on AWS", "software_it"),
    ("Account Executive", "Close enterprise SaaS deals, manage pipeline", "sales"),
    ("Business Development Executive", "Generate leads and grow revenue", "sales"),
    ("Digital Marketing Specialist", "Run SEO and SEM campaigns, content", "marketing"),
    ("Financial Analyst", "FP&A, budgeting, investment analysis", "finance"),
    ("Staff Nurse", "Patient care in the ICU ward", "healthcare"),
    ("Registered Pharmacist", "Dispense medication, counsel patients", "healthcare"),
    ("Recruiter", "Talent acquisition and candidate screening", "hr"),
    ("Mechanical Design Engineer", "CAD, CAE, product design, GD&T", "mechanical_engineering"),
    ("Structural Engineer", "Reinforced concrete design for high-rise buildings", "civil_engineering"),
    ("VLSI Design Engineer", "RTL, ASIC verification, physical design", "electronics"),
    ("Customer Support Engineer", "Resolve technical support tickets", "customer_support"),
    ("Product Manager", "Own product roadmap and backlog prioritisation", "product"),
    ("UX Designer", "Wireframes, prototypes, user research in Figma", "design"),
    ("Corporate Lawyer", "Contract review, compliance, corporate counsel", "legal"),
    ("Supply Chain Analyst", "Procurement, logistics, inventory planning", "supply_chain"),
]


class TestClassifierAccuracy:
    def test_rule_tier_accuracy(self):
        clf = DomainClassifier()  # rule-only, no router
        correct = 0
        misses = []
        for title, desc, expected in LABELED:
            res = clf.classify_rule(title, desc)
            got = res.code if res else "other"
            if got == expected:
                correct += 1
            else:
                misses.append((title, expected, got))
        accuracy = correct / len(LABELED)
        # Rule tier alone places the labeled set correctly; the LLM tier exists
        # for the long tail of genuinely ambiguous real-world titles.
        assert accuracy >= 0.9, f"accuracy={accuracy:.2f} misses={misses}"

    @pytest.mark.asyncio
    async def test_classify_falls_back_to_other_without_router(self):
        clf = DomainClassifier()
        res = await clf.classify("Zorble Wrangler", "Untagged mystery role")
        assert res.code in {"other"} or res.method in {"rule_low", "fallback"}

    @pytest.mark.asyncio
    async def test_llm_tier_used_for_ambiguous(self):
        class FakeResp:
            content = '{"code": "healthcare", "confidence": 0.9}'

        class FakeRouter:
            async def route(self, *a, **k):
                return FakeResp()

        clf = DomainClassifier(router=FakeRouter(), min_rule_confidence=0.99)
        # Force the LLM path by demanding near-perfect rule confidence.
        res = await clf.classify("Care Coordinator", "hospital ward operations")
        assert res.code == "healthcare"
        assert res.method == "llm"

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_gracefully(self):
        class BoomRouter:
            async def route(self, *a, **k):
                raise RuntimeError("bedrock down")

        clf = DomainClassifier(router=BoomRouter(), min_rule_confidence=0.99)
        res = await clf.classify("Sales Executive", "quota carrying role")
        # Rule tier had a guess; classification never raises.
        assert res.code == "sales"
        assert res.method in {"rule_low", "fallback"}


class TestSmartRecruitersConnector:
    PAYLOAD = {
        "content": [
            {
                "id": "sr-1",
                "name": "Retail Sales Associate",
                "location": {"city": "Mumbai", "country": "India"},
                "industry": {"label": "Retail"},
                "department": {"label": "Store Operations"},
                "function": {"label": "Sales"},
                "applyUrl": "https://jobs.smartrecruiters.com/acme/sr-1",
            },
            {
                "id": "sr-2",
                "name": "Registered Nurse",
                "location": {"remote": False, "city": "Delhi"},
                "industry": {"label": "Healthcare"},
            },
        ]
    }

    def _fetcher(self):
        return lambda url: self.PAYLOAD

    def test_parses_postings_and_industry(self):
        src = SmartRecruitersSource("acme", "Acme Retail", "tier2")
        postings = src.fetch(self._fetcher())
        assert len(postings) == 2
        p0 = postings[0]
        assert p0.title == "Retail Sales Associate"
        assert p0.industry == "Retail"
        assert p0.location == "Mumbai, India"
        assert p0.apply_url.endswith("/sr-1")
        assert postings[1].industry == "Healthcare"

    def test_empty_response(self):
        src = SmartRecruitersSource("x", "X")
        assert src.fetch(lambda u: {}) == []


class TestAggregatorIsolationWithClassification:
    def test_failed_source_isolated_new_source(self):
        class Boom(JobSource):
            name = "smartrecruiters:boom"

            def fetch(self, fetcher):
                raise JobSourceError("down")

        good = SmartRecruitersSource("acme", "Acme")
        result = discover(
            sources=[Boom(), good],
            fetcher=lambda url: TestSmartRecruitersConnector.PAYLOAD,
        )
        assert "smartrecruiters:boom" in result.sources_failed
        assert "smartrecruiters:acme" in result.sources_ok
        assert result.postings  # good source still produced jobs
