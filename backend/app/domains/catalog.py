"""EMBEDHUNT AI — Domain taxonomy catalog (single source of truth).

A plug-and-play HIERARCHY: Domain → Sub-domain → (roles as keywords). Nothing
here is hardcoded into logic — add a domain/sub-domain by adding a node and the
migration + classifier + app pick it up automatically. The self-referential
model (parent_id + level) supports arbitrary nesting for the future.

Both the Alembic migration and scripts/seed.py import from here so the taxonomy
can never drift. Domain ids are deterministic (uuid5) so migrations can backfill
FKs by code without a round-trip.

Design notes:
  * ``embedded_engineering`` keeps its Phase-1 code/id (existing rows reference
    it) and its weighted SkillCategories — it simply gains a parent (IT).
  * ``roles`` on a node are the discriminative title keywords the classifier's
    cheap rule tier matches on before ever calling the LLM. A domain's effective
    keyword set is its own roles plus all of its descendants' roles.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

# Fixed namespace → stable ids across migration runs, seed runs, and machines.
_NS = uuid.UUID("e3b0c442-98fc-1c14-9afb-4c8996fb9242")


@dataclass
class Node:
    code: str
    name: str
    description: str = ""
    roles: tuple[str, ...] = ()          # discriminative role/title keywords
    children: tuple["Node", ...] = ()


# ── The taxonomy tree (data, not logic) ──────────────────────────────────────
TAXONOMY: tuple[Node, ...] = (
    Node("software_it", "Information Technology",
         "Software, data, cloud, security, embedded and all IT roles.",
         roles=("software engineer", "developer", "programmer", "sde", "it "),
         children=(
             Node("software_development", "Software Development",
                  roles=("backend engineer", "frontend engineer", "full stack",
                         "web developer", "mobile developer", "api developer",
                         "platform engineer", "android developer", "ios developer",
                         "flutter developer", "react developer", "angular developer",
                         "node.js", "java backend", "python developer", "golang",
                         "php developer", "javascript", "typescript", ".net")),
             Node("ai_ml", "AI & Machine Learning",
                  roles=("machine learning engineer", "ml engineer", "ai engineer",
                         "deep learning", "nlp engineer", "computer vision",
                         "llm engineer", "generative ai", "prompt engineer",
                         "mlops", "ai research")),
             Node("data_analytics", "Data & Analytics",
                  roles=("data engineer", "data scientist", "data analyst",
                         "business intelligence", "analytics engineer",
                         "etl developer", "bi developer", "data entry")),
             Node("cloud", "Cloud",
                  roles=("aws engineer", "azure engineer", "gcp engineer",
                         "cloud architect", "cloud consultant", "cloud engineer")),
             Node("devops_sre", "DevOps & SRE",
                  roles=("devops engineer", "site reliability", "sre",
                         "build engineer", "release engineer", "platform engineer")),
             Node("cybersecurity", "Cybersecurity",
                  roles=("security engineer", "soc analyst", "penetration tester",
                         "ethical hacker", "security architect", "iam engineer",
                         "cybersecurity", "infosec")),
             Node("networking", "Networking",
                  roles=("network engineer", "network architect", "wireless engineer",
                         "firewall engineer")),
             Node("embedded_engineering", "Embedded Systems",
                  roles=("embedded software", "embedded engineer", "firmware",
                         "embedded linux", "autosar", "device driver", "bsp engineer",
                         "rtos", "microcontroller", "adas", "ecu ", "functional safety",
                         "aspice", "perception engineer")),
             Node("qa_testing", "QA & Testing",
                  roles=("manual tester", "automation tester", "performance tester",
                         "sdet", "test architect", "qa engineer")),
             Node("database", "Database",
                  roles=("dba", "database engineer", "sql developer", "nosql")),
             Node("blockchain", "Blockchain",
                  roles=("solidity", "blockchain engineer", "smart contract")),
             Node("game_dev", "Game Development",
                  roles=("unity developer", "unreal developer", "gameplay engineer",
                         "graphics engineer")),
         )),
    Node("electronics", "Electronics",
         "Hardware, VLSI, PCB, RF and semiconductor design.",
         roles=("hardware engineer", "pcb designer", "fpga engineer", "asic engineer",
                "vlsi engineer", "vlsi design", "rf engineer", "analog engineer",
                "digital design", "verification engineer", "validation engineer",
                "physical design", "semiconductor")),
    Node("mechanical_engineering", "Mechanical Engineering",
         "Design, manufacturing, CAD/CAE, robotics, HVAC.",
         roles=("mechanical design", "cad engineer", "cae engineer",
                "manufacturing engineer", "tool design", "production engineer",
                "hvac engineer", "robotics engineer")),
    Node("electrical_engineering", "Electrical Engineering",
         "Power systems, control, automation, PLC.",
         roles=("electrical design", "power systems", "protection engineer",
                "plc engineer", "automation engineer", "control systems")),
    Node("civil_engineering", "Civil Engineering",
         "Structural, construction, site and planning.",
         roles=("structural engineer", "site engineer", "construction engineer",
                "quantity surveyor", "bim engineer", "planning engineer")),
    Node("architecture", "Architecture",
         "Architecture, interior, landscape and urban planning.",
         roles=("architect", "interior designer", "landscape architect",
                "urban planner")),
    Node("healthcare", "Healthcare & Life Sciences",
         "Clinical, nursing, pharma and allied health.",
         roles=("doctor", "surgeon", "dentist", "nurse", "pharmacist",
                "physiotherapist", "radiologist", "medical lab", "clinical")),
    Node("finance", "Finance & Accounting",
         "Accounting, analysis, audit, tax and planning.",
         roles=("accountant", "financial analyst", "investment banker", "auditor",
                "tax consultant", "risk analyst", "equity research", "financial planner")),
    Node("banking", "Banking",
         "Retail, corporate and treasury banking.",
         roles=("relationship manager", "credit analyst", "loan officer",
                "treasury analyst", "branch manager")),
    Node("sales", "Sales & Business Development",
         "Inside/field sales, account management, BD.",
         roles=("sales executive", "business development", "sales manager",
                "account executive", "enterprise sales", "sdr", "bdr")),
    Node("marketing", "Marketing & Growth",
         "Digital, content, brand and product marketing.",
         roles=("digital marketing", "seo specialist", "sem specialist",
                "content marketer", "social media manager", "brand manager",
                "product marketing", "growth marketer")),
    Node("product", "Product Management",
         "Product management and ownership.",
         roles=("product manager", "associate product manager", "product owner",
                "technical product manager")),
    Node("design", "Design",
         "UI/UX, product, graphic and motion design.",
         roles=("ui designer", "ux designer", "product designer", "graphic designer",
                "motion designer", "illustrator", "3d artist")),
    Node("hr", "Human Resources",
         "Recruiting, HRBP, payroll and L&D.",
         roles=("recruiter", "talent acquisition", "hr business partner",
                "payroll specialist", "learning & development", "hr manager")),
    Node("legal", "Legal",
         "Counsel, compliance and legal advisory.",
         roles=("lawyer", "corporate counsel", "legal advisor", "compliance officer",
                "paralegal")),
    Node("education", "Education",
         "Teaching, academia and curriculum.",
         roles=("teacher", "professor", "lecturer", "curriculum developer",
                "research assistant", "tutor")),
    Node("research", "Research",
         "Research science and engineering.",
         roles=("research scientist", "research engineer", "data researcher",
                "lab scientist")),
    Node("manufacturing", "Manufacturing",
         "Production, process and quality engineering.",
         roles=("production engineer", "process engineer", "quality engineer",
                "plant manager")),
    Node("supply_chain", "Supply Chain",
         "Procurement, logistics and warehousing.",
         roles=("supply chain analyst", "procurement specialist", "logistics manager",
                "warehouse manager")),
    Node("operations", "Operations",
         "Operations, program and project management.",
         roles=("operations manager", "operations analyst", "program manager",
                "project manager")),
    Node("customer_support", "Customer Support",
         "Support, success and implementation.",
         roles=("customer support", "technical support", "customer success",
                "implementation engineer", "support engineer")),
    Node("hospitality", "Hospitality",
         "Hotels, restaurants and front office.",
         roles=("hotel manager", "chef", "restaurant manager", "front office")),
    Node("aviation", "Aviation",
         "Flight, maintenance and cabin crew.",
         roles=("pilot", "aircraft maintenance", "cabin crew", "flight dispatcher")),
    Node("government", "Government & Public Sector",
         "Civil service, defence and administration.",
         roles=("civil servant", "police officer", "defence officer",
                "public administration")),
    Node("creative_media", "Creative & Media",
         "Editing, journalism and content creation.",
         roles=("video editor", "photographer", "animator", "journalist",
                "content creator", "copywriter")),
    Node("consulting", "Consulting & Freelance",
         "Independent and advisory roles.",
         roles=("freelancer", "technical consultant", "business consultant",
                "ai consultant", "cloud consultant")),
    Node("other", "Other",
         "Roles that do not yet map to a specialised domain."),
)

DEFAULT_DOMAIN_CODE = "embedded_engineering"

# FROZEN — the flat 13 domains Phase 1's migration (b2c3d4e5f6a7) seeded. Kept
# byte-stable so that historical migration's import + behaviour never changes;
# Phase 2's migration transforms these into the hierarchical TAXONOMY above.
# Do NOT edit — evolve the live taxonomy through TAXONOMY + a new migration.
DOMAINS: list[tuple[str, str, str]] = [
    ("embedded_engineering", "Embedded & Systems Engineering",
     "Firmware, RTOS, microcontrollers, protocols, automotive and hardware."),
    ("software_it", "Software & IT",
     "Full-stack, backend, frontend, mobile, DevOps, cloud and data engineering."),
    ("data_analytics", "Data & Analytics",
     "Data analysis, data science, BI, ML engineering and data entry."),
    ("sales", "Sales & Business Development",
     "Inside/field sales, account management, business development."),
    ("marketing", "Marketing & Growth",
     "Digital marketing, content, brand, SEO/SEM, growth and product marketing."),
    ("finance_accounting", "Finance & Accounting",
     "Accounting, FP&A, audit, taxation, treasury and investment analysis."),
    ("hr", "Human Resources",
     "Recruiting, HR operations, L&D, compensation and people partnering."),
    ("bpo_support", "BPO & Customer Support",
     "Customer service, technical support, back-office and contact-centre roles."),
    ("healthcare", "Healthcare & Life Sciences",
     "Clinical, nursing, pharma, medical devices and allied health."),
    ("mechanical_engineering", "Mechanical Engineering",
     "Design, manufacturing, CAD/CAE, thermal, automotive mechanical."),
    ("civil_engineering", "Civil Engineering",
     "Structural, construction, site, transportation and geotechnical."),
    ("operations_supply_chain", "Operations & Supply Chain",
     "Operations, logistics, procurement, planning and warehouse management."),
    ("other", "Other",
     "Roles that do not yet map to a specialised domain."),
]

# Phase-1 codes that the hierarchical taxonomy supersedes (unreferenced — only
# embedded_engineering was ever backfilled onto rows). Phase 2's migration
# removes these so the live set matches TAXONOMY exactly.
OBSOLETE_DOMAIN_CODES: list[str] = [
    "finance_accounting", "bpo_support", "operations_supply_chain",
]

# Embedded engineering's SkillCategories — migrated verbatim from the matcher's
# hardcoded WEIGHTS so behaviour is unchanged. (code, name, weight)
EMBEDDED_CATEGORIES: list[tuple[str, str, int]] = [
    ("programming", "Programming Languages", 20),
    ("rtos_os", "RTOS & Operating Systems", 20),
    ("protocols", "Protocols & Communication", 20),
    ("hardware", "Hardware Platforms", 15),
    ("automotive", "Automotive & Safety", 15),
    ("tools", "Tools & Debugging", 5),
    ("concepts", "Software Concepts", 5),
]


def domain_id(code: str) -> str:
    """Deterministic id for a domain code."""
    return str(uuid.uuid5(_NS, f"domain:{code}"))


def skill_category_id(domain_code: str, category_code: str) -> str:
    """Deterministic id for a domain's skill category."""
    return str(uuid.uuid5(_NS, f"skillcat:{domain_code}:{category_code}"))


def skill_id(domain_code: str, category_code: str, skill_name: str) -> str:
    """Deterministic id for a single skill row."""
    return str(uuid.uuid5(_NS, f"skill:{domain_code}:{category_code}:{skill_name.lower()}"))


@dataclass
class FlatDomain:
    code: str
    name: str
    description: str
    parent_code: str | None
    level: int
    keywords: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return domain_id(self.code)

    @property
    def parent_id(self) -> str | None:
        return domain_id(self.parent_code) if self.parent_code else None


def _own_keywords(node: Node) -> list[str]:
    return [node.name.lower(), *node.roles]


def _descendant_keywords(node: Node) -> list[str]:
    kws = list(node.roles)
    for c in node.children:
        kws.extend(_descendant_keywords(c))
    return kws


def flatten() -> list[FlatDomain]:
    """Depth-first flatten of the tree into rows for seeding/migration.

    A node's ``keywords`` include its own roles plus every descendant's roles,
    so the classifier can resolve any child title to its top-level domain.
    """
    out: list[FlatDomain] = []

    def walk(node: Node, parent: str | None, level: int) -> None:
        kws = sorted(set(_own_keywords(node) + _descendant_keywords(node)))
        out.append(FlatDomain(node.code, node.name, node.description,
                              parent, level, kws))
        for child in node.children:
            walk(child, node.code, level + 1)

    for root in TAXONOMY:
        walk(root, None, 0)
    return out


def top_level_domains() -> list[FlatDomain]:
    """Level-0 domains only — the classifier's coarse tagging target set."""
    return [d for d in flatten() if d.level == 0]


_ID_TO_CODE: dict[str, str] | None = None


def code_for_domain_id(did: str | None) -> str | None:
    """Reverse the deterministic id → domain code mapping (cached)."""
    global _ID_TO_CODE
    if _ID_TO_CODE is None:
        _ID_TO_CODE = {domain_id(d.code): d.code for d in flatten()}
    return _ID_TO_CODE.get(did) if did else None
