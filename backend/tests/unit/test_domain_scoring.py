"""Phase 3 — scoring correctness for the newly seeded domains (software_it,
sales, finance), the DB config loader, domain routing in rank_jobs, and
domain-aware prompt rendering."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.domains.catalog import domain_id
from app.domains.skill_seed import DOMAIN_SKILL_SEED
from app.llm.prompts import GAP_ANALYSIS, JOB_MATCH
from app.models.domain_taxonomy import JobDomain, Skill, SkillCategory
from app.recommendation.matcher import CategoryConfig, DomainScoringConfig, compute_match
from app.recommendation.ranking import rank_jobs
from app.recommendation.scoring_config import load_scoring_configs
from app.resume.normalizer import CandidateProfile


def _config_from_seed(domain_code: str) -> DomainScoringConfig:
    """Build a config directly from the seed data (mirrors the DB loader)."""
    cats = []
    for ccode, _cn, weight, skills in DOMAIN_SKILL_SEED[domain_code]:
        canonical = set()
        alias_pairs = []
        for name, aliases in skills:
            canonical.add(name.lower())
            alias_pairs.extend((a.lower(), name.lower()) for a in aliases)
        cats.append(CategoryConfig(ccode, weight, frozenset(canonical), None,
                                   alias_pairs=tuple(alias_pairs)))
    return DomainScoringConfig(domain_code, tuple(cats), embedded_bonus=False)


# ── Scoring correctness per domain ──────────────────────────────────────────
class TestNewDomainScoring:
    def test_sales_strong_candidate(self):
        cfg = _config_from_seed("sales")
        profile = CandidateProfile(total_years_experience=5.0, all_skills=[
            "prospecting", "lead generation", "pipeline management", "negotiation",
            "closing", "salesforce", "hubspot", "b2b sales", "saas", "relationship management",
        ])
        m = compute_match(
            profile, "Enterprise Account Executive",
            "Own the full sales cycle: prospecting, pipeline management, negotiation and closing. Salesforce CRM.",
            "prospecting,pipeline management,negotiation,closing,salesforce,b2b sales",
            exp_min=3, config=cfg)
        assert m.total_score >= 70            # strong sales fit scores high
        assert "salesforce" in m.matched_skills
        # Explanation uses sales category names, never embedded jargon.
        assert "rtos" not in m.explanation.lower() and "firmware" not in m.explanation.lower()

    def test_finance_partial_candidate(self):
        cfg = _config_from_seed("finance")
        profile = CandidateProfile(total_years_experience=2.0, all_skills=[
            "accounting", "reconciliation", "excel", "tally",
        ])
        m = compute_match(
            profile, "Accounts Executive",
            "Core accounting, bank reconciliation, GST, month-end close using Tally and Excel.",
            "accounting,reconciliation,gst,tally,excel,financial reporting",
            exp_min=1, config=cfg)
        assert 30 <= m.total_score < 90       # partial coverage → mid score
        assert "accounting" in m.matched_skills

    def test_software_it_candidate(self):
        cfg = _config_from_seed("software_it")
        profile = CandidateProfile(total_years_experience=4.0, all_skills=[
            "python", "django", "postgresql", "aws", "docker", "kubernetes", "rest api", "git",
        ])
        m = compute_match(
            profile, "Senior Backend Engineer",
            "Build Python/Django services with PostgreSQL, deploy on AWS with Docker and Kubernetes. REST APIs.",
            "python,django,postgresql,aws,docker,kubernetes,rest api",
            exp_min=3, config=cfg)
        assert m.total_score >= 70
        assert {"python", "aws", "docker"} <= set(m.matched_skills)

    def test_cross_domain_candidate_scores_low(self):
        # An embedded engineer's skills shouldn't match a sales job well.
        cfg = _config_from_seed("sales")
        embedded = CandidateProfile(all_skills=["c", "rtos", "can", "arm", "firmware"])
        m = compute_match(embedded, "Sales Executive", "Prospecting and closing deals.",
                          "prospecting,closing,salesforce", config=cfg)
        assert m.total_score < 30


# ── DB config loader ────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def seeded_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        # Seed the three domains + their categories/skills.
        for dcode, cats in DOMAIN_SKILL_SEED.items():
            s.add(JobDomain(id=domain_id(dcode), code=dcode, name=dcode.title(), level=0))
            for ccode, cname, weight, skills in cats:
                from app.domains.catalog import skill_category_id, skill_id
                cid = skill_category_id(dcode, ccode)
                s.add(SkillCategory(id=cid, domain_id=domain_id(dcode), code=ccode, name=cname, weight=weight))
                for name, aliases in skills:
                    s.add(Skill(id=skill_id(dcode, ccode, name), category_id=cid, name=name, aliases=list(aliases)))
        await s.flush()
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_loader_builds_domain_configs(seeded_db):
    configs = await load_scoring_configs(seeded_db)
    assert {"software_it", "sales", "finance"} <= set(configs)
    sales = configs["sales"]
    assert sum(c.weight for c in sales.categories) == 100
    assert not sales.embedded_bonus
    # A known sales skill is present in some category's vocab.
    assert any("salesforce" in c.vocab for c in sales.categories)


@pytest.mark.asyncio
async def test_rank_jobs_routes_by_domain(seeded_db):
    configs = await load_scoring_configs(seeded_db)
    profile = CandidateProfile(total_years_experience=5.0, all_skills=[
        "prospecting", "negotiation", "closing", "salesforce", "b2b sales", "pipeline management",
    ])
    jobs = [{
        "id": "sales-1", "title": "Account Executive", "company": "Acme",
        "description": "Prospecting, pipeline management, negotiation, closing with Salesforce.",
        "required_skills": "prospecting,pipeline management,negotiation,closing,salesforce",
        "domain_id": domain_id("sales"), "experience_min": 3,
    }]
    result = rank_jobs(profile, jobs, min_score=0, scoring=configs)
    assert result.jobs and result.jobs[0].match_score >= 70


# ── Domain-aware prompts ────────────────────────────────────────────────────
class TestDomainAwarePrompts:
    _EMBEDDED_JARGON = ("rtos", "firmware", "autosar", "embedded", "cortex", "can bus")
    _SALES_JARGON = ("prospecting", "quota", "salesforce", "pipeline")

    def test_sales_render_has_no_embedded_jargon(self):
        text = (JOB_MATCH.render(domain="Sales & Business Development",
                                 candidate_profile="{}", job="{}")
                + JOB_MATCH.system_prompt).lower()
        assert "sales & business development" in text
        assert not any(j in text for j in self._EMBEDDED_JARGON)

    def test_embedded_render_has_no_sales_jargon(self):
        text = (GAP_ANALYSIS.render(domain="Embedded & Systems Engineering",
                                    candidate_profile="{}", job="{}")
                + GAP_ANALYSIS.system_prompt).lower()
        assert "embedded & systems engineering" in text
        assert not any(j in text for j in self._SALES_JARGON)
