"""EMBEDHUNT AI — Real SkillCategory + Skill seed data for the first wave of
non-embedded domains (Phase 3): software_it, sales, finance.

Each domain's category weights sum to 100 (same scale as the embedded profile,
so match_scores are comparable across domains). Weights encode what actually
drives hiring in each field; skills carry aliases for synonym matching.

Domains NOT in this map are intentionally left with empty SkillCategory sets —
see the TODO in scripts/seed.py. We do not fabricate weights for domains without
researched data; the ranking layer uses a generic skill-overlap fallback for
them until their real taxonomies land in a later phase.

Shape: {domain_code: [(category_code, category_name, weight,
                        [(skill_name, [aliases...]), ...]), ...]}
"""
from __future__ import annotations

DOMAIN_SKILL_SEED: dict[str, list] = {
    # ── General software / IT (non-embedded) ────────────────────────────────
    # Programming + architecture dominate; cloud/devops is now core; data and
    # testing/tooling support.
    "software_it": [
        ("programming_frameworks", "Programming & Frameworks", 25, [
            ("python", ["py"]), ("java", []), ("javascript", ["js"]),
            ("typescript", ["ts"]), ("go", ["golang"]), ("rust", []),
            ("c#", ["csharp", ".net"]), ("php", []), ("ruby", ["rails"]),
            ("react", ["react.js", "reactjs"]), ("angular", []), ("vue", ["vue.js"]),
            ("node.js", ["node", "nodejs"]), ("django", []), ("flask", []),
            ("spring boot", ["spring"]), ("express", ["express.js"]),
            ("next.js", ["nextjs"]), ("kotlin", []), ("swift", []),
        ]),
        ("system_design", "System Design & Architecture", 20, [
            ("rest api", ["rest", "restful"]), ("graphql", []),
            ("microservices", ["micro services"]), ("system design", []),
            ("design patterns", []), ("api design", []),
            ("distributed systems", []), ("scalability", []),
            ("kafka", []), ("grpc", []), ("message queue", ["rabbitmq"]),
        ]),
        ("databases", "Databases & Data", 15, [
            ("sql", []), ("postgresql", ["postgres"]), ("mysql", []),
            ("mongodb", ["mongo"]), ("redis", []), ("nosql", []),
            ("elasticsearch", ["elastic search"]), ("oracle", []),
            ("dynamodb", []), ("database design", []),
        ]),
        ("cloud_devops", "Cloud & DevOps", 20, [
            ("aws", ["amazon web services"]), ("azure", []), ("gcp", ["google cloud"]),
            ("docker", []), ("kubernetes", ["k8s"]), ("ci/cd", ["cicd", "ci cd"]),
            ("terraform", []), ("jenkins", []), ("devops", []),
            ("linux", []), ("ansible", []),
        ]),
        ("testing_quality", "Testing & Quality", 10, [
            ("unit testing", []), ("integration testing", []),
            ("tdd", ["test driven development"]), ("pytest", []),
            ("jest", []), ("selenium", []), ("test automation", []),
        ]),
        ("tools_collaboration", "Tools & Collaboration", 10, [
            ("git", []), ("agile", []), ("scrum", []), ("jira", []),
            ("github", []), ("gitlab", []),
        ]),
    ],

    # ── Sales & business development ─────────────────────────────────────────
    # Prospecting + closing drive revenue; CRM tooling is essential; domain
    # knowledge + communication support.
    "sales": [
        ("prospecting_pipeline", "Prospecting & Pipeline", 30, [
            ("prospecting", []), ("lead generation", ["lead gen"]),
            ("pipeline management", ["pipeline"]), ("cold calling", ["cold call"]),
            ("lead qualification", ["qualification"]), ("outbound", ["outbound sales"]),
            ("inbound", ["inbound sales"]), ("sales development", ["sdr", "bdr"]),
            ("demand generation", ["demand gen"]), ("account research", []),
        ]),
        ("closing_negotiation", "Closing & Negotiation", 25, [
            ("negotiation", []), ("closing", ["deal closing"]),
            ("objection handling", []), ("contract negotiation", []),
            ("upselling", ["upsell"]), ("cross-selling", ["cross sell"]),
            ("quota attainment", ["quota"]), ("deal management", []),
        ]),
        ("crm_tools", "CRM & Sales Tools", 20, [
            ("salesforce", ["sfdc"]), ("hubspot", []), ("crm", []),
            ("outreach", []), ("salesloft", []), ("zoho crm", ["zoho"]),
            ("pipedrive", []), ("linkedin sales navigator", ["sales navigator"]),
        ]),
        ("domain_knowledge", "Domain & Industry Knowledge", 15, [
            ("saas", ["saas sales"]), ("b2b sales", ["b2b"]),
            ("enterprise sales", ["enterprise"]), ("solution selling", []),
            ("consultative selling", []), ("product knowledge", []),
            ("industry knowledge", []),
        ]),
        ("communication_relationship", "Communication & Relationships", 10, [
            ("relationship management", []), ("presentation", ["presentations"]),
            ("communication", []), ("account management", []),
            ("customer relationship", []),
        ]),
    ],

    # ── Finance & accounting ─────────────────────────────────────────────────
    # Matches the deliverable's suggested categories: core accounting, modeling/
    # Excel, compliance/regulatory, tools (SAP/Tally/QuickBooks), reporting.
    "finance": [
        ("core_accounting", "Core Accounting", 30, [
            ("accounting", []), ("bookkeeping", []), ("general ledger", ["gl"]),
            ("accounts payable", ["ap"]), ("accounts receivable", ["ar"]),
            ("reconciliation", ["bank reconciliation"]), ("gaap", []),
            ("journal entries", []), ("financial statements", []),
            ("month-end close", ["month end close", "closing"]),
        ]),
        ("financial_modeling", "Financial Modeling & Analysis", 25, [
            ("financial modeling", ["financial modelling"]),
            ("excel", ["advanced excel", "ms excel"]), ("valuation", []),
            ("forecasting", []), ("budgeting", ["budget"]),
            ("fp&a", ["fpa", "fp and a"]), ("variance analysis", []),
            ("dcf", ["discounted cash flow"]), ("financial analysis", []),
        ]),
        ("compliance_regulatory", "Compliance & Regulatory", 20, [
            ("audit", ["auditing", "statutory audit"]), ("taxation", ["tax"]),
            ("ifrs", []), ("sox", ["sarbanes oxley"]),
            ("regulatory compliance", ["compliance"]), ("internal controls", []),
            ("gst", []), ("tax compliance", []),
        ]),
        ("tools_systems", "Tools & Systems", 15, [
            ("sap", ["sap fico"]), ("tally", []), ("quickbooks", []),
            ("oracle financials", ["oracle"]), ("netsuite", []),
            ("xero", []), ("erp", []),
        ]),
        ("reporting_communication", "Reporting & Communication", 10, [
            ("financial reporting", ["reporting"]), ("mis reporting", ["mis"]),
            ("presentation", []), ("stakeholder management", []),
            ("dashboards", ["dashboard"]),
        ]),
    ],
}


def seeded_domain_codes() -> list[str]:
    return list(DOMAIN_SKILL_SEED)
