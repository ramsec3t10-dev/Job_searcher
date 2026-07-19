"""Unit tests for the job-discovery subsystem (app.job_sources).

All HTTP is mocked via an injected fetcher — these tests never touch the network
and are fully deterministic.
"""
from __future__ import annotations

import pytest

from app.job_sources.aggregator import discover
from app.job_sources.base import JobSource, JobSourceError
from app.job_sources.greenhouse import GreenhouseSource
from app.job_sources.lever import LeverSource
from app.job_sources.remoteok import RemoteOkSource
from app.job_sources.schema import JobPosting, parse_min_experience, strip_html

# ── Fixtures: realistic API payload shapes ───────────────────────────────────

GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 101,
            "title": "Senior Embedded Software Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
            "location": {"name": "Bangalore, India"},
            "content": "<p>Firmware for ARM Cortex-M. 5+ years of C, RTOS, CAN, SPI, I2C.</p>",
        },
        {
            "id": 102,
            "title": "Account Executive",  # must be filtered out (sales)
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/102",
            "location": {"name": "Remote"},
            "content": "<p>Close enterprise deals.</p>",
        },
    ]
}

LEVER_PAYLOAD = [
    {
        "id": "abc",
        "text": "Linux Kernel Engineer",
        "hostedUrl": "https://jobs.lever.co/startup/abc",
        "categories": {"location": "Pune, India", "team": "Platform"},
        "descriptionPlain": "Linux kernel, device drivers, BSP, Yocto, C, 3 years experience.",
    }
]

REMOTEOK_PAYLOAD = [
    {"legal": "RemoteOK API notice — no 'position' key here, must be skipped"},
    {
        "id": "ro-1",
        "position": "Embedded Firmware Engineer",
        "company": "RemoteCo",
        "location": "Worldwide",
        "tags": ["c", "rtos", "embedded"],
        "description": "Build firmware",
        "url": "https://remoteok.com/jobs/ro-1",
    },
]


def make_fetcher(mapping: dict[str, object]):
    def _fetch(url: str):
        for key, payload in mapping.items():
            if key in url:
                return payload
        raise JobSourceError(f"no fixture for {url}")
    return _fetch


# ── schema helpers ───────────────────────────────────────────────────────────

class TestSchemaHelpers:
    def test_strip_html_unescapes_and_strips_tags(self):
        assert strip_html("<p>C &amp; C++</p>") == "C & C++"

    def test_strip_html_empty(self):
        assert strip_html(None) == ""

    def test_parse_min_experience(self):
        assert parse_min_experience("5+ years of C") == 5
        assert parse_min_experience("between 3-8 years") == 3
        assert parse_min_experience("no numbers here") is None

    def test_posting_extracts_skills_from_description(self):
        p = JobPosting(
            external_id="1", title="Embedded Engineer", company="Acme",
            location="Pune", apply_url="u", description="C, RTOS, CAN, SPI experience",
            source_portal="greenhouse:acme", source_url="u",
        )
        assert "c" in p.required_skills
        assert "rtos" in p.required_skills
        assert "can" in p.required_skills

    def test_corpus_dict_shape(self):
        p = JobPosting(
            external_id="1", title="Embedded Engineer", company="Acme",
            location="Pune", apply_url="u", description="C and RTOS",
            source_portal="greenhouse:acme", source_url="u", company_tier="tier1_software",
        )
        d = p.to_corpus_dict()
        assert set(d) >= {
            "id", "title", "company", "company_tier", "location", "source_portal",
            "source_url", "apply_url", "description", "required_skills",
            "experience_min", "experience_max", "salary_min_lpa", "salary_max_lpa",
        }
        assert d["id"] == "greenhouse:acme:1"
        assert isinstance(d["required_skills"], str)

    def test_relevance_keeps_all_domains(self):
        # Multi-domain (Phase 2): non-engineering roles are now KEPT and tagged
        # by the classifier downstream — no longer filtered out at ingestion.
        sales = JobPosting(
            external_id="1", title="Account Executive", company="Acme",
            location="Remote", apply_url="u", description="Sell things",
            source_portal="x", source_url="u",
        )
        assert sales.is_relevant() is True

    def test_relevance_includes_engineer(self):
        p = JobPosting(
            external_id="1", title="Firmware Engineer", company="Acme",
            location="Pune", apply_url="u", description="C, RTOS",
            source_portal="x", source_url="u",
        )
        assert p.is_relevant() is True

    def test_relevance_drops_invalid(self):
        # Structurally invalid rows (missing title/company) are still dropped.
        p = JobPosting(
            external_id="1", title="", company="",
            location="Remote", apply_url="u", description="x",
            source_portal="x", source_url="u",
        )
        assert p.is_relevant() is False


# ── connectors ───────────────────────────────────────────────────────────────

class TestGreenhouse:
    def test_parses_jobs(self):
        src = GreenhouseSource("acme", "Acme", "tier1_software")
        postings = src.fetch(make_fetcher({"boards-api.greenhouse.io": GREENHOUSE_PAYLOAD}))
        assert len(postings) == 2
        eng = postings[0]
        assert eng.title == "Senior Embedded Software Engineer"
        assert eng.company == "Acme"
        assert eng.location == "Bangalore, India"
        assert eng.source_portal == "greenhouse:acme"
        assert "<p>" not in eng.description
        assert eng.experience_min == 5

    def test_empty_response(self):
        src = GreenhouseSource("acme", "Acme")
        assert src.fetch(make_fetcher({"greenhouse": {"jobs": []}})) == []


class TestLever:
    def test_parses_jobs(self):
        src = LeverSource("startup", "Startup", "tier2_automotive")
        postings = src.fetch(make_fetcher({"api.lever.co": LEVER_PAYLOAD}))
        assert len(postings) == 1
        assert postings[0].title == "Linux Kernel Engineer"
        assert postings[0].location == "Pune, India"
        assert postings[0].source_portal == "lever:startup"


class TestRemoteOk:
    def test_skips_legal_notice(self):
        src = RemoteOkSource()
        postings = src.fetch(make_fetcher({"remoteok.com/api": REMOTEOK_PAYLOAD}))
        assert len(postings) == 1
        assert postings[0].title == "Embedded Firmware Engineer"
        assert postings[0].company == "RemoteCo"


# ── aggregator ───────────────────────────────────────────────────────────────

class TestAggregator:
    def _all_sources(self):
        return [
            GreenhouseSource("acme", "Acme", "tier1_software"),
            LeverSource("startup", "Startup", "tier2_automotive"),
            RemoteOkSource(),
        ]

    def _fetcher(self):
        return make_fetcher({
            "boards-api.greenhouse.io": GREENHOUSE_PAYLOAD,
            "api.lever.co": LEVER_PAYLOAD,
            "remoteok.com/api": REMOTEOK_PAYLOAD,
        })

    def test_discovers_all_domains(self):
        result = discover(sources=self._all_sources(), fetcher=self._fetcher())
        titles = {p.title for p in result.postings}
        # Multi-domain: the sales role is now KEPT alongside engineering roles.
        assert "Account Executive" in titles
        assert "Senior Embedded Software Engineer" in titles
        assert "Linux Kernel Engineer" in titles
        assert "Embedded Firmware Engineer" in titles
        assert set(result.sources_ok) == {"greenhouse:acme", "lever:startup", "remoteok"}
        assert result.sources_failed == []

    def test_corpus_dicts_match_engine_schema(self):
        result = discover(sources=self._all_sources(), fetcher=self._fetcher())
        corpus = result.to_corpus()
        assert corpus
        for job in corpus:
            assert job["id"] and job["title"] and job["company"]
            assert isinstance(job["required_skills"], str)

    def test_dedup_across_sources(self):
        dup = [
            GreenhouseSource("acme", "Acme", "tier1_software"),
            GreenhouseSource("acme", "Acme", "tier1_software"),
        ]
        result = discover(sources=dup, fetcher=self._fetcher())
        # The two identical boards each return the same 2 distinct postings;
        # dedup collapses them to those 2 unique (company, title) pairs.
        assert len(result.postings) == 2
        keys = [p.dedup_key for p in result.postings]
        assert len(keys) == len(set(keys))   # no duplicates survive

    def test_failed_source_is_isolated(self):
        class Boom(JobSource):
            name = "boom"
            def fetch(self, fetcher):
                raise JobSourceError("down")

        sources = [Boom(), GreenhouseSource("acme", "Acme")]
        result = discover(sources=sources, fetcher=self._fetcher())
        assert "boom" in result.sources_failed
        assert "greenhouse:acme" in result.sources_ok
        assert len(result.postings) >= 1

    def test_limit_per_source(self):
        result = discover(sources=[GreenhouseSource("acme", "Acme")],
                          fetcher=self._fetcher(), limit_per_source=1)
        assert len(result.postings) == 1


# ── integration with the recommendation engine ───────────────────────────────

class TestEngineIntegration:
    def test_run_live_matching_merges_and_ranks(self):
        from app.recommendation.engine import run_live_matching
        from app.resume.normalizer import CandidateProfile

        profile = CandidateProfile(
            name_hint="Test", total_years_experience=5.0, is_embedded_engineer=True,
            programming_languages=["c", "c++"],
            rtos_and_os=["rtos", "linux kernel"],
            protocols=["can", "spi", "i2c"],
            hardware_platforms=["arm", "cortex-m"],
            software_concepts=["device driver", "bsp"],
            all_skills=["c", "c++", "rtos", "can", "spi", "i2c", "arm",
                        "cortex-m", "device driver", "bsp", "linux kernel"],
            skill_count=11, embedded_domain_score=80,
        )
        fetcher = make_fetcher({
            "boards-api.greenhouse.io": GREENHOUSE_PAYLOAD,
            "api.lever.co": LEVER_PAYLOAD,
            "remoteok.com/api": REMOTEOK_PAYLOAD,
        })
        # Only greenhouse source via a tiny registry override is complex; instead
        # discover with explicit sources by monkeypatching default via fetcher.
        result, discovery = run_live_matching(profile, fetcher=fetcher)
        assert result.total_scanned >= 1
        assert isinstance(discovery.sources_ok, list)

    def test_agent_runs_on_live_discovery(self):
        from app.agent.executor import CareerCopilotAgent
        from app.resume.normalizer import CandidateProfile

        profile = CandidateProfile(
            name_hint="Test", total_years_experience=5.0, is_embedded_engineer=True,
            programming_languages=["c", "c++"], rtos_and_os=["rtos", "linux kernel"],
            protocols=["can", "spi", "i2c"], hardware_platforms=["arm", "cortex-m"],
            software_concepts=["device driver", "bsp"],
            all_skills=["c", "c++", "rtos", "can", "spi", "i2c", "arm",
                        "cortex-m", "device driver", "bsp", "linux kernel"],
            skill_count=11, embedded_domain_score=80,
        )
        fetcher = make_fetcher({
            "boards-api.greenhouse.io": GREENHOUSE_PAYLOAD,
            "api.lever.co": LEVER_PAYLOAD,
            "remoteok.com/api": REMOTEOK_PAYLOAD,
        })
        report = CareerCopilotAgent("u1").run(profile, live=True, fetcher=fetcher)
        # The trace must record the discovery phase and the report must serialize.
        phases = {entry["phase"] for entry in report.memory.to_dict()["trace"]}
        assert "discover" in phases
        assert isinstance(report.to_dict(), dict)
