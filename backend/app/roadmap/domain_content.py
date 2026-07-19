"""EMBEDHUNT AI — Domain learning content (Phase 5).

Per-domain skill *progression order*, learning *hours*, and real *resources* for
the domains seeded in Phase 3 (software_it, sales, finance). Keyed by the same
canonical skill names the Phase-3 skill taxonomy uses, so a job's missing_skills
(produced by the domain-aware matcher) resolve to the right learning material.

Embedded stays entirely on its existing planner tables (SKILL_HOURS /
SKILL_RESOURCES in app/roadmap/planner.py) — untouched here, so embedded roadmaps
are byte-identical. Only non-embedded domains route through this module.
"""
from __future__ import annotations

# Ordered learning progression per domain (foundational → advanced). Roadmaps
# order a candidate's missing skills by their position here.
PROGRESSION: dict[str, list[str]] = {
    "software_it": [
        "git", "python", "sql", "rest api", "unit testing", "postgresql",
        "docker", "system design", "microservices", "aws", "kubernetes", "ci/cd",
    ],
    "sales": [
        # Cold outreach → discovery → objection handling → negotiation → complex closing
        "prospecting", "lead generation", "salesforce", "crm",
        "consultative selling", "objection handling", "negotiation", "closing",
        "pipeline management", "b2b sales", "enterprise sales",
    ],
    "finance": [
        "accounting", "bookkeeping", "reconciliation", "excel",
        "financial modeling", "financial analysis", "budgeting", "forecasting",
        "audit", "taxation", "sap", "tally", "financial reporting",
    ],
}

# Learning hours per skill (best-effort, realistic full effort).
HOURS: dict[str, dict[str, int]] = {
    "software_it": {
        "git": 8, "python": 40, "sql": 20, "rest api": 20, "unit testing": 15,
        "postgresql": 20, "docker": 20, "system design": 40, "microservices": 30,
        "aws": 35, "kubernetes": 35, "ci/cd": 15,
    },
    "sales": {
        "prospecting": 15, "lead generation": 15, "salesforce": 20, "crm": 12,
        "consultative selling": 25, "objection handling": 15, "negotiation": 25,
        "closing": 20, "pipeline management": 15, "b2b sales": 20, "enterprise sales": 30,
    },
    "finance": {
        "accounting": 40, "bookkeeping": 20, "reconciliation": 15, "excel": 25,
        "financial modeling": 40, "financial analysis": 30, "budgeting": 20,
        "forecasting": 20, "audit": 35, "taxation": 30, "sap": 30, "tally": 15,
        "financial reporting": 20,
    },
}

# Named, real resources per skill.
RESOURCES: dict[str, dict[str, list[dict]]] = {
    "software_it": {
        "python": [{"title": "Automate the Boring Stuff — free", "type": "book", "url": "https://automatetheboringstuff.com"}],
        "system design": [{"title": "System Design Primer (GitHub) — free", "type": "docs", "url": "https://github.com/donnemartin/system-design-primer"}],
        "aws": [{"title": "AWS Cloud Practitioner Essentials — free", "type": "course", "url": "https://explore.skillbuilder.aws"}],
        "docker": [{"title": "Docker official get-started", "type": "docs", "url": "https://docs.docker.com/get-started/"}],
        "kubernetes": [{"title": "Kubernetes Basics tutorial", "type": "docs", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/"}],
        "sql": [{"title": "SQLBolt — interactive SQL — free", "type": "course", "url": "https://sqlbolt.com"}],
        "git": [{"title": "Pro Git — free official book", "type": "book", "url": "https://git-scm.com/book/en/v2"}],
    },
    "sales": {
        "prospecting": [{"title": "Fanatical Prospecting (Jeb Blount)", "type": "book", "url": "https://www.salesgravy.com/fanatical-prospecting/"}],
        "negotiation": [{"title": "Never Split the Difference (Chris Voss)", "type": "book", "url": "https://www.blackswanltd.com/never-split-the-difference"}],
        "salesforce": [{"title": "Salesforce Trailhead — free", "type": "course", "url": "https://trailhead.salesforce.com"}],
        "consultative selling": [{"title": "SPIN Selling (Neil Rackham)", "type": "book", "url": "https://en.wikipedia.org/wiki/SPIN_selling"}],
        "closing": [{"title": "The JOLT Effect (Dixon & McKenna)", "type": "book", "url": "https://www.jolteffect.com"}],
        "b2b sales": [{"title": "HubSpot Sales Software certification — free", "type": "course", "url": "https://academy.hubspot.com"}],
    },
    "finance": {
        "financial modeling": [{"title": "CFI Financial Modeling course", "type": "course", "url": "https://corporatefinanceinstitute.com/course/financial-modeling/"}],
        "excel": [{"title": "ExcelJet formulas & functions — free", "type": "docs", "url": "https://exceljet.net"}],
        "accounting": [{"title": "AccountingCoach — free", "type": "course", "url": "https://www.accountingcoach.com"}],
        "audit": [{"title": "ICAI / ACCA audit study resources", "type": "docs", "url": "https://www.accaglobal.com/gb/en/student/exam-support-resources.html"}],
        "sap": [{"title": "SAP Learning Hub — FICO fundamentals", "type": "course", "url": "https://learning.sap.com"}],
        "financial analysis": [{"title": "CFI Financial Analysis fundamentals", "type": "course", "url": "https://corporatefinanceinstitute.com"}],
    },
}

# Non-embedded default (never the embedded firmware blog).
DEFAULT_RESOURCES: dict[str, list[dict]] = {
    "software_it": [{"title": "roadmap.sh — developer roadmaps", "type": "docs", "url": "https://roadmap.sh"}],
    "sales": [{"title": "HubSpot Academy — free sales courses", "type": "course", "url": "https://academy.hubspot.com"}],
    "finance": [{"title": "Corporate Finance Institute (CFI)", "type": "course", "url": "https://corporatefinanceinstitute.com"}],
}

_GENERIC_DEFAULT = [{"title": "Coursera / LinkedIn Learning — search this skill", "type": "course", "url": "https://www.coursera.org"}]
_DEFAULT_HOURS = 25


def has_domain(domain_code: str) -> bool:
    return domain_code in PROGRESSION


def order_skills(domain_code: str, skills: list[str]) -> list[str]:
    """Order missing skills by the domain's learning progression; unknown skills
    keep their original relative order after the known ones."""
    chain = PROGRESSION.get(domain_code, [])
    pos = {s: i for i, s in enumerate(chain)}
    return sorted(skills, key=lambda s: (pos.get(s.lower(), len(chain) + 1),))


def hours_for(domain_code: str, skill: str) -> int:
    return HOURS.get(domain_code, {}).get(skill.lower(), _DEFAULT_HOURS)


def resources_for(domain_code: str, skill: str) -> list[dict]:
    dom = RESOURCES.get(domain_code, {})
    return dom.get(skill.lower()) or DEFAULT_RESOURCES.get(domain_code) or _GENERIC_DEFAULT
