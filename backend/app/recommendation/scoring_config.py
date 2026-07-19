"""EMBEDHUNT AI — Domain scoring config loader (Phase 3).

Builds per-domain ``DomainScoringConfig`` objects from the SkillCategory / Skill
rows seeded per domain, so the recommendation engine's category weights are
data-driven instead of hardcoded.

Resolution rules:
  * ``embedded_engineering`` reuses the in-code skill vocabularies and profile
    buckets (the authoritative embedded matching path) but takes its weights
    from the DB rows — proven identical to the pre-Phase-3 scoring by
    tests/unit/test_scoring_regression.py.
  * Any other domain with seeded categories builds its vocabularies from that
    domain's Skill rows (name + aliases), scored against the candidate's
    ``all_skills``.
  * Domains without seeded categories are simply absent from the registry; the
    ranking layer falls back to a generic skill-overlap config for those.

The registry is small static reference data, so callers may cache it per request.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog import DEFAULT_DOMAIN_CODE, domain_id
from app.models.domain_taxonomy import JobDomain, Skill, SkillCategory
from app.recommendation.matcher import (
    CATEGORY_SETS, PROFILE_ATTRS, CategoryConfig, DomainScoringConfig,
    embedded_default_config,
)


async def load_scoring_configs(db: AsyncSession) -> dict[str, DomainScoringConfig]:
    """Return ``{domain_code: DomainScoringConfig}`` for every domain that has
    seeded skill categories. Embedded always resolves (in-code vocab + DB weights)."""
    domains = {d.id: d for d in (await db.execute(select(JobDomain))).scalars().all()}
    cats = (await db.execute(select(SkillCategory))).scalars().all()
    skills = (await db.execute(select(Skill))).scalars().all()

    skills_by_cat: dict[str, list[Skill]] = {}
    for s in skills:
        skills_by_cat.setdefault(s.category_id, []).append(s)

    cats_by_domain: dict[str, list[SkillCategory]] = {}
    for c in cats:
        cats_by_domain.setdefault(c.domain_id, []).append(c)

    configs: dict[str, DomainScoringConfig] = {}
    emb_id = domain_id(DEFAULT_DOMAIN_CODE)

    for did, domain_cats in cats_by_domain.items():
        domain = domains.get(did)
        if domain is None:
            continue
        code = domain.code
        if code == DEFAULT_DOMAIN_CODE:
            # Weights from DB, vocab/buckets from the authoritative in-code sets.
            db_weights = {c.code: c.weight for c in domain_cats}
            cfg_cats = tuple(
                CategoryConfig(cc, db_weights.get(cc, w),
                               frozenset(CATEGORY_SETS[cc]), PROFILE_ATTRS[cc])
                for cc, w in _embedded_weight_order()
            )
            configs[code] = DomainScoringConfig(code, cfg_cats, embedded_bonus=True)
            continue

        cfg_cats = []
        for c in sorted(domain_cats, key=lambda x: (-x.weight, x.code)):
            canonical: set[str] = set()
            alias_pairs: list[tuple[str, str]] = []
            for sk in skills_by_cat.get(c.id, []):
                name = sk.name.strip().lower()
                canonical.add(name)
                for alias in (sk.aliases or []):
                    if alias:
                        alias_pairs.append((str(alias).strip().lower(), name))
            if not canonical:
                continue  # a category with no skills contributes nothing
            cfg_cats.append(CategoryConfig(
                c.code, c.weight, frozenset(canonical), None,
                alias_pairs=tuple(alias_pairs)))
        if cfg_cats:
            configs[code] = DomainScoringConfig(code, tuple(cfg_cats), embedded_bonus=False)

    # Guarantee embedded is always available even if its category rows are missing.
    configs.setdefault(DEFAULT_DOMAIN_CODE, embedded_default_config())
    return configs


def _embedded_weight_order():
    """Embedded (code, weight) in the canonical order the pre-Phase-3 code used,
    so category-score ordering (and thus explanations) stay identical."""
    from app.recommendation.matcher import WEIGHTS
    return list(WEIGHTS.items())
