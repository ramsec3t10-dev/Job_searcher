"""EMBEDHUNT AI — Knowledge Architecture: layer registry.

The knowledge stack is a *dependency-ordered* sequence of domains. Each layer
may read the layers above it (the "↓" edges in the architecture), so the order
below is authoritative — the assembler walks it top-to-bottom and every provider
sees the already-assembled upstream context.

    User → Career Twin → Memory → Knowledge Graph → Skills → Companies → Jobs
    → Projects → Learning → Interview → Market → Salary → Goals → Habits
    → Health (optional) → Professional Growth

The vertical stack *produces* a per-user :class:`KnowledgeContext`; the
horizontal AI Orchestrator *consumes* it. Most layers are backed by models that
already exist in the repo (see ``backing``); ``Health`` is declared but has no
backing yet (the optional layer), so it is marked ``planned``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class KnowledgeLayer(str, Enum):
    """The 16 knowledge layers, declared in dependency order (top → bottom)."""

    USER = "user"
    CAREER_TWIN = "career_twin"
    MEMORY = "memory"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SKILLS = "skills"
    COMPANIES = "companies"
    JOBS = "jobs"
    PROJECTS = "projects"
    LEARNING = "learning"
    INTERVIEW = "interview"
    MARKET = "market"
    SALARY = "salary"
    GOALS = "goals"
    HABITS = "habits"
    HEALTH = "health"
    PROFESSIONAL_GROWTH = "professional_growth"


# Status of a layer's provider implementation.
IMPLEMENTED = "implemented"
PLANNED = "planned"


@dataclass(frozen=True)
class LayerSpec:
    layer: KnowledgeLayer
    title: str
    status: str
    backing: str
    description: str


# Registry — the single source of truth for what each layer is and where its
# data comes from. Ordering follows the KnowledgeLayer enum definition order.
LAYER_SPECS: dict[KnowledgeLayer, LayerSpec] = {
    KnowledgeLayer.USER: LayerSpec(
        KnowledgeLayer.USER, "User", IMPLEMENTED, "models.user + candidate_profiles",
        "Account identity, role, and profile completeness — the root of the stack.",
    ),
    KnowledgeLayer.CAREER_TWIN: LayerSpec(
        KnowledgeLayer.CAREER_TWIN, "Career Twin", IMPLEMENTED, "career_twins",
        "Living, versioned source of truth aggregating skills, experience, salary and goals.",
    ),
    KnowledgeLayer.MEMORY: LayerSpec(
        KnowledgeLayer.MEMORY, "Memory", IMPLEMENTED, "memory_entries",
        "Importance-ranked long-term memories recalled across sessions.",
    ),
    KnowledgeLayer.KNOWLEDGE_GRAPH: LayerSpec(
        KnowledgeLayer.KNOWLEDGE_GRAPH, "Knowledge Graph", IMPLEMENTED, "skill_nodes/skill_edges",
        "Deterministic skill graph answering prerequisites/learning-paths with zero LLM.",
    ),
    KnowledgeLayer.SKILLS: LayerSpec(
        KnowledgeLayer.SKILLS, "Skills", IMPLEMENTED, "career_twins.skills + knowledge_graph",
        "The candidate's skills and, via the graph, the gaps to their target role.",
    ),
    KnowledgeLayer.COMPANIES: LayerSpec(
        KnowledgeLayer.COMPANIES, "Companies", IMPLEMENTED, "companies + job_recommendations",
        "Dream companies and the companies surfacing the strongest matches.",
    ),
    KnowledgeLayer.JOBS: LayerSpec(
        KnowledgeLayer.JOBS, "Jobs", IMPLEMENTED, "applications + job_recommendations + discovered_jobs",
        "Application pipeline, recommendations and live-market job counts.",
    ),
    KnowledgeLayer.PROJECTS: LayerSpec(
        KnowledgeLayer.PROJECTS, "Projects", IMPLEMENTED, "career_twins.projects",
        "Portfolio projects that evidence the candidate's skills.",
    ),
    KnowledgeLayer.LEARNING: LayerSpec(
        KnowledgeLayer.LEARNING, "Learning", IMPLEMENTED, "learning_roadmaps",
        "Active learning roadmap and progress toward a target role.",
    ),
    KnowledgeLayer.INTERVIEW: LayerSpec(
        KnowledgeLayer.INTERVIEW, "Interview", IMPLEMENTED, "interview_sessions + career_twins",
        "Interview readiness, prep sessions and weak topics.",
    ),
    KnowledgeLayer.MARKET: LayerSpec(
        KnowledgeLayer.MARKET, "Market", IMPLEMENTED, "discovered_jobs (corpus)",
        "Live embedded-job market snapshot: volume, hirers and salary bands.",
    ),
    KnowledgeLayer.SALARY: LayerSpec(
        KnowledgeLayer.SALARY, "Salary", IMPLEMENTED, "career_twins + market",
        "Current vs. target compensation and market value.",
    ),
    KnowledgeLayer.GOALS: LayerSpec(
        KnowledgeLayer.GOALS, "Goals", IMPLEMENTED, "career_twins.career_goals",
        "Short- and long-term career goals and target role.",
    ),
    KnowledgeLayer.HABITS: LayerSpec(
        KnowledgeLayer.HABITS, "Habits", IMPLEMENTED, "daily_checkins + career_twins",
        "Learning streaks and check-in consistency.",
    ),
    KnowledgeLayer.HEALTH: LayerSpec(
        KnowledgeLayer.HEALTH, "Health", PLANNED, "—",
        "Optional wellbeing/burnout signals. No backing store yet — declared for completeness.",
    ),
    KnowledgeLayer.PROFESSIONAL_GROWTH: LayerSpec(
        KnowledgeLayer.PROFESSIONAL_GROWTH, "Professional Growth", IMPLEMENTED,
        "career_twins + applications",
        "Trajectory signals: twin versioning, learning velocity and outcomes.",
    ),
}


def ordered_layers() -> list[KnowledgeLayer]:
    """Return every layer in dependency order (top → bottom of the stack)."""
    return list(KnowledgeLayer)


def implemented_layers() -> list[KnowledgeLayer]:
    return [layer for layer, spec in LAYER_SPECS.items() if spec.status == IMPLEMENTED]
