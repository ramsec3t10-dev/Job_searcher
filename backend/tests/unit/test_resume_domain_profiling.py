"""Phase 4 — domain-aware resume profiling: embedded regression (identical
output), new-domain extractors, resume domain classification accuracy, and the
generic fallback for un-plugged domains."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.settings import settings
from app.database.base import Base
from app.domains.catalog import domain_id
from app.resume.extractor import extract_experience, extract_skills
from app.resume.normalizer import build_profile
from app.agents.skill_extractors import (
    ResumeDomainClassifier, extractors_for, get_extractor, has_plugin,
)
from app.agents.skill_extractors.finance import FinanceSkillExtractor
from app.agents.skill_extractors.sales import SalesSkillExtractor
from app.agents.skill_extractors.software_it import SoftwareITSkillExtractor
from app.models.profile import CandidateProfile
from app.services.resume_service import ResumeService


# ── Labeled resume fixtures (role line first for the role_hint) ─────────────
EMBEDDED = """Arjun Rao
Senior Embedded Software Engineer
2018 - Present  Bosch, Firmware Engineer
Firmware for ARM Cortex-M. RTOS, FreeRTOS, C, C++, CAN, SPI, I2C, device drivers,
AUTOSAR, ISO 26262, bootloader, bare metal. B.E. Electronics, 2017."""

SALES = """Rahul Verma
Senior Account Executive
2019 - Present  Acme SaaS, Account Executive
Enterprise SaaS sales. Achieved 135% of quota. Skills: prospecting, pipeline
management, negotiation, closing, Salesforce, HubSpot, B2B sales, consultative selling.
Sold into fintech and healthcare. MBA Marketing 2018."""

FINANCE = """Priya Nair
Finance Manager
2017 - Present  KPMG, Finance Manager
FP&A and audit. Skills: financial modeling, advanced excel, budgeting, forecasting,
SAP, Tally, GST, reconciliation. Chartered Accountant (CA), CFA Level 2. M.Com 2016."""

SOFTWARE = """Neha Gupta
Senior Backend Engineer
2019 - Present  Flipkart, Backend Engineer
Python, Django, PostgreSQL, Redis, AWS, Docker, Kubernetes, REST API, microservices,
CI/CD, git. B.Tech Computer Science 2018."""

HEALTHCARE = """Dr. Sunil Menon
Consultant Cardiologist
2015 - Present  Apollo Hospitals, Cardiologist
Skills: cardiology, echocardiography, patient care, clinical diagnosis, ECG, angioplasty.
MBBS, MD Cardiology 2014."""

LABELED = [
    (EMBEDDED, "embedded_engineering"),
    (SALES, "sales"),
    (FINANCE, "finance"),
    (SOFTWARE, "software_it"),
]


def _legacy_ai_summary(text: str) -> str:
    return build_profile(text, extract_skills(text), extract_experience(text)).to_json()


@pytest_asyncio.fixture
async def svc(monkeypatch):
    # Deterministic: no LLM tier during tests (rule-tier classification only).
    monkeypatch.setattr(settings, "LLM_ENRICHMENT_ENABLED", False)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield ResumeService(s)
    await engine.dispose()


# ── 1. CRITICAL regression: embedded profiling unchanged ────────────────────
@pytest.mark.asyncio
async def test_embedded_ai_summary_identical(svc):
    exp = extract_experience(EMBEDDED)
    skills = extract_skills(EMBEDDED)
    profile = build_profile(EMBEDDED, skills, exp)
    before = profile.to_json()
    assert before == _legacy_ai_summary(EMBEDDED)   # sanity: fixtures deterministic

    meta = await svc._profile_domains("u-emb", EMBEDDED, exp, profile)

    assert meta["primary"] == "embedded_engineering"
    assert profile.to_json() == before              # byte-identical — no mutation


# ── 2. Resume domain classification accuracy ────────────────────────────────
def test_classification_accuracy():
    clf = ResumeDomainClassifier()
    correct, misses = 0, []
    for text, expected in LABELED:
        role = extract_experience(text).current_role or ""
        res = clf.classify_rule(text, role_hint=role)
        got = res.primary if res else "other"
        if got == expected:
            correct += 1
        else:
            misses.append((expected, got))
    assert correct == len(LABELED), f"misses={misses}"


# ── 3. New-domain extractors produce structured data ────────────────────────
class TestExtractors:
    @pytest.mark.asyncio
    async def test_sales(self):
        r = await SalesSkillExtractor().extract(SALES)
        assert r.profiling_level == "full"
        assert r.structured["quota_attainment_pct"] == 135
        assert "salesforce" in r.structured["crm_tools"]
        assert "fintech" in r.structured["industries_sold_into"]

    @pytest.mark.asyncio
    async def test_finance(self):
        r = await FinanceSkillExtractor().extract(FINANCE)
        assert "ca" in r.structured["certifications"] and "cfa" in r.structured["certifications"]
        assert "sap" in r.structured["tools"] and "tally" in r.structured["tools"]
        assert "fp&a" in r.structured["functional_areas"]

    @pytest.mark.asyncio
    async def test_software_it(self):
        r = await SoftwareITSkillExtractor().extract(SOFTWARE)
        assert "python" in r.structured["languages"]
        assert "aws" in r.structured["cloud_platforms"]
        assert r.structured["has_devops"] is True


# ── 4. Generic fallback for un-plugged domains ──────────────────────────────
class TestGenericFallback:
    def test_healthcare_has_no_plugin(self):
        assert not has_plugin("healthcare")

    @pytest.mark.asyncio
    async def test_generic_basic_profiling(self):
        ext = get_extractor("healthcare")
        assert ext.domain_code == "healthcare"
        r = await ext.extract(HEALTHCARE)
        assert r.profiling_level == "basic"
        assert any("cardiology" in s or "ecg" in s or "patient care" in s for s in r.skills)


# ── 5. Non-embedded end-to-end: skills merged + candidate_profiles written ──
@pytest.mark.asyncio
async def test_sales_profiling_persists_and_merges(svc):
    exp = extract_experience(SALES)
    profile = build_profile(SALES, extract_skills(SALES), exp)
    meta = await svc._profile_domains("u-sales", SALES, exp, profile)

    assert meta["primary"] == "sales"
    # Sales skills merged into all_skills so matching has signal.
    assert "salesforce" in [s.lower() for s in profile.all_skills]

    row = (await svc.db.execute(
        __import__("sqlalchemy").select(CandidateProfile).where(
            CandidateProfile.user_id == "u-sales"))).scalar_one_or_none()
    assert row is not None
    assert row.primary_domain_id == domain_id("sales")
    assert "sales" in row.domain_profile_data
    assert row.domain_profile_data["sales"]["structured"]["quota_attainment_pct"] == 135


@pytest.mark.asyncio
async def test_career_switcher_secondary_domain(svc):
    # Resume with both software and sales signals → secondary detected.
    text = """Alex Kim
Sales Engineer
2020 - Present  DevTools Inc, Sales Engineer
Technical pre-sales. Skills: prospecting, closing, salesforce, b2b sales, negotiation,
python, aws, docker, kubernetes, rest api, pipeline management, consultative selling."""
    exp = extract_experience(text)
    profile = build_profile(text, extract_skills(text), exp)
    meta = await svc._profile_domains("u-switch", text, exp, profile)
    assert meta["primary"] in {"sales", "software_it"}
    row = (await svc.db.execute(
        __import__("sqlalchemy").select(CandidateProfile).where(
            CandidateProfile.user_id == "u-switch"))).scalar_one_or_none()
    # domain_profile_data holds every extractor that ran.
    assert len(row.domain_profile_data) >= 1
