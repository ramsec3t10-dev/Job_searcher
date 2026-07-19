"""Shared: build a canonical→aliases skill map for a domain from the Phase-3
seed data (single source of truth), so extractors and matching agree on vocab."""
from __future__ import annotations

from app.domains.skill_seed import DOMAIN_SKILL_SEED


def vocab_for(domain_code: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for _ccode, _cname, _weight, skills in DOMAIN_SKILL_SEED.get(domain_code, []):
        for name, aliases in skills:
            out[name.lower()] = [a.lower() for a in aliases]
    return out
