"""EMBEDHUNT AI — Job-source registry.

Maps target companies to their hosting ATS so discovery has a concrete, curated
starting set. Board tokens/slugs are the public identifiers used in each ATS's
career-page URL. They are data, not code: extend or correct this registry (or
load it from config) without touching connector logic. Unknown/incorrect tokens
fail gracefully per-source in the aggregator.

NOTE: Many large semiconductor/automotive firms use Workday/Eightfold rather than
Greenhouse/Lever; those require dedicated connectors and are intentionally out of
scope for this slice. The startups/scale-ups below genuinely use Greenhouse/Lever.
"""
from __future__ import annotations

from app.job_sources.base import JobSource
from app.job_sources.greenhouse import GreenhouseSource
from app.job_sources.lever import LeverSource
from app.job_sources.remoteok import RemoteOkSource
from app.job_sources.smartrecruiters import SmartRecruitersSource

# (board_token, display_name, company_tier)
GREENHOUSE_BOARDS: list[tuple[str, str, str]] = [
    ("databricks", "Databricks", "tier1_software"),
    ("cruise", "Cruise", "tier2_automotive"),
    ("zoox", "Zoox", "tier2_automotive"),
    ("samsara", "Samsara", "tier3_industrial"),
    ("anduril", "Anduril Industries", "tier3_industrial"),
    ("waymo", "Waymo", "tier2_automotive"),
]

# (company_slug, display_name, company_tier)
LEVER_COMPANIES: list[tuple[str, str, str]] = [
    ("netflix", "Netflix", "tier1_software"),
    ("plaid", "Plaid", "tier1_software"),
]

# (company_identifier, display_name, company_tier) — SmartRecruiters-hosted
# boards spanning many industries (retail, hospitality, health, sales) so
# discovery reaches well beyond engineering. Identifiers are the public company
# slugs used in jobs.smartrecruiters.com URLs; unknown ones fail per-source.
SMARTRECRUITERS_COMPANIES: list[tuple[str, str, str]] = [
    ("Ubisoft2", "Ubisoft", "tier2_gaming"),
    ("Bosch", "Bosch", "tier1_automotive"),
    ("Visa", "Visa", "tier1_finance"),
]


def default_sources() -> list[JobSource]:
    """Build the curated default set of legitimate discovery sources."""
    sources: list[JobSource] = []
    for token, name, tier in GREENHOUSE_BOARDS:
        sources.append(GreenhouseSource(token, name, tier))
    for slug, name, tier in LEVER_COMPANIES:
        sources.append(LeverSource(slug, name, tier))
    for cid, name, tier in SMARTRECRUITERS_COMPANIES:
        sources.append(SmartRecruitersSource(cid, name, tier))
    sources.append(RemoteOkSource())
    return sources
