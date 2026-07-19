"""Infer a subrole_code from a job title (Phase 7).

Produces a normalized snake_case key (e.g. "Senior Backend Engineer" →
"backend_engineer", "Account Executive" → "account_executive") used to look up
curated questions. Seniority words are stripped so a title maps to the same
subrole regardless of level. This is a best-effort key, not a taxonomy.
"""
from __future__ import annotations

import re

_SENIORITY = {"senior", "junior", "lead", "principal", "staff", "sr", "jr",
              "associate", "entry", "level", "i", "ii", "iii", "chief", "head", "of"}


def infer_subrole(title: str) -> str:
    if not title:
        return ""
    # Keep the part before a separator (e.g. "Firmware Engineer - ADAS").
    base = re.split(r"[-–—/(,|]", title)[0]
    tokens = re.findall(r"[a-z0-9+#.]+", base.lower())
    kept = [t for t in tokens if t not in _SENIORITY]
    return "_".join(kept).strip("_")
