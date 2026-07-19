"""Extractor registry — maps a domain code to its plugin, with the generic
fallback for domains that have no dedicated extractor yet."""
from __future__ import annotations

from app.agents.skill_extractors.base import SkillExtractor
from app.agents.skill_extractors.embedded import EmbeddedSkillExtractor
from app.agents.skill_extractors.finance import FinanceSkillExtractor
from app.agents.skill_extractors.generic import GenericSkillExtractor
from app.agents.skill_extractors.sales import SalesSkillExtractor
from app.agents.skill_extractors.software_it import SoftwareITSkillExtractor

# Domains with a dedicated, researched plugin (full profiling).
_PLUGINS: dict[str, type[SkillExtractor]] = {
    "embedded_engineering": EmbeddedSkillExtractor,
    "software_it": SoftwareITSkillExtractor,
    "sales": SalesSkillExtractor,
    "finance": FinanceSkillExtractor,
}


def has_plugin(domain_code: str) -> bool:
    return domain_code in _PLUGINS


def get_extractor(domain_code: str, router=None) -> SkillExtractor:
    cls = _PLUGINS.get(domain_code)
    if cls is not None:
        return cls()
    # No dedicated plugin → generic basic profiling, tagged with the real domain.
    return GenericSkillExtractor(router=router, domain_code=domain_code)


def extractors_for(primary: str, secondary: list[str] | None = None,
                   router=None) -> list[SkillExtractor]:
    """Extractor(s) to run for a candidate: primary plus any confidently-detected
    secondary domains (career switchers), de-duplicated, primary first."""
    codes: list[str] = [primary]
    for c in (secondary or []):
        if c and c not in codes:
            codes.append(c)
    return [get_extractor(c, router) for c in codes]
