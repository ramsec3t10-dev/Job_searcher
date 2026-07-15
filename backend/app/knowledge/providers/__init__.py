"""Knowledge-layer providers.

``default_providers()`` returns one provider instance per *implemented* layer,
in dependency order. The ``Health`` layer is intentionally absent — it is
declared ``planned`` in the registry and the assembler records it as skipped.
"""
from app.knowledge.base import KnowledgeLayerProvider
from app.knowledge.providers.core import (
    CareerTwinProvider,
    KnowledgeGraphProvider,
    MemoryProvider,
    UserProvider,
)
from app.knowledge.providers.growth import (
    GoalsProvider,
    HabitsProvider,
    InterviewProvider,
    LearningProvider,
    ProfessionalGrowthProvider,
)
from app.knowledge.providers.opportunities import (
    CompaniesProvider,
    JobsProvider,
    MarketProvider,
    ProjectsProvider,
    SalaryProvider,
    SkillsProvider,
)


def default_providers() -> list[KnowledgeLayerProvider]:
    """Every implemented layer provider (order is normalised by the assembler)."""
    return [
        UserProvider(),
        CareerTwinProvider(),
        MemoryProvider(),
        KnowledgeGraphProvider(),
        SkillsProvider(),
        CompaniesProvider(),
        JobsProvider(),
        ProjectsProvider(),
        LearningProvider(),
        InterviewProvider(),
        MarketProvider(),
        SalaryProvider(),
        GoalsProvider(),
        HabitsProvider(),
        ProfessionalGrowthProvider(),
    ]


__all__ = ["default_providers"]
