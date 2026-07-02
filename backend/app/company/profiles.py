"""EMBEDHUNT AI — Company intelligence profiles.

Enriches the target :data:`REGISTRY` with structured, product-curated
intelligence: tech stack, embedded domains, salary bands (LPA), interview
process, difficulty, and a preparation focus. Marquee companies have explicit
overrides; every other registry company inherits sensible tier defaults, so all
55 targets always resolve to a complete profile. This is curated reference data,
not scraped content.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.company.intelligence import REGISTRY, CompanyTarget, CompanyTier


@dataclass
class CompanyProfile:
    name: str
    tier: str
    careers_url: str
    priority: int
    india_office: bool
    interview_rounds: str
    interview_difficulty: str
    salary_min_lpa: float
    salary_max_lpa: float
    tech_stack: list[str] = field(default_factory=list)
    embedded_domains: list[str] = field(default_factory=list)
    prep_focus: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tier": self.tier,
            "careers_url": self.careers_url,
            "priority": self.priority,
            "india_office": self.india_office,
            "interview_rounds": self.interview_rounds,
            "interview_difficulty": self.interview_difficulty,
            "salary_band_lpa": [self.salary_min_lpa, self.salary_max_lpa],
            "tech_stack": self.tech_stack,
            "embedded_domains": self.embedded_domains,
            "prep_focus": self.prep_focus,
        }


# Tier-level defaults (difficulty, rounds, salary band, typical stack/domains).
_TIER_DEFAULTS: dict[CompanyTier, dict] = {
    CompanyTier.TIER1_SEMICONDUCTOR: {
        "interview_rounds": "5-8", "interview_difficulty": "very_high",
        "salary_min_lpa": 25.0, "salary_max_lpa": 55.0,
        "tech_stack": ["c", "c++", "arm", "rtos", "device driver"],
        "embedded_domains": ["soc", "firmware", "low-level"],
        "prep_focus": ["data structures", "c internals", "computer architecture"],
    },
    CompanyTier.TIER2_AUTOMOTIVE: {
        "interview_rounds": "4-6", "interview_difficulty": "high",
        "salary_min_lpa": 15.0, "salary_max_lpa": 32.0,
        "tech_stack": ["c", "autosar", "can", "iso 26262", "misra c"],
        "embedded_domains": ["automotive", "functional safety", "ecu"],
        "prep_focus": ["autosar", "iso 26262", "can/lin"],
    },
    CompanyTier.TIER3_INDUSTRIAL: {
        "interview_rounds": "3-5", "interview_difficulty": "medium",
        "salary_min_lpa": 12.0, "salary_max_lpa": 26.0,
        "tech_stack": ["c", "c++", "modbus", "freertos", "mqtt"],
        "embedded_domains": ["industrial iot", "automation"],
        "prep_focus": ["rtos", "communication protocols", "control systems"],
    },
    CompanyTier.TIER4_TELECOM: {
        "interview_rounds": "4-6", "interview_difficulty": "high",
        "salary_min_lpa": 18.0, "salary_max_lpa": 38.0,
        "tech_stack": ["c", "linux kernel", "device driver", "tcp/ip", "ethernet"],
        "embedded_domains": ["networking", "linux platform"],
        "prep_focus": ["linux internals", "networking", "device drivers"],
    },
    CompanyTier.TIER5_CONSUMER: {
        "interview_rounds": "4-6", "interview_difficulty": "high",
        "salary_min_lpa": 18.0, "salary_max_lpa": 40.0,
        "tech_stack": ["c", "c++", "rtos", "ble", "power management"],
        "embedded_domains": ["consumer devices", "wireless"],
        "prep_focus": ["low power", "wireless protocols", "c++"],
    },
    CompanyTier.TIER6_DEFENSE: {
        "interview_rounds": "3-5", "interview_difficulty": "high",
        "salary_min_lpa": 14.0, "salary_max_lpa": 30.0,
        "tech_stack": ["c", "ada", "vxworks", "do-178c"],
        "embedded_domains": ["avionics", "defense"],
        "prep_focus": ["safety-critical", "rtos", "certification standards"],
    },
    CompanyTier.INDIA_FOCUSED: {
        "interview_rounds": "3-5", "interview_difficulty": "medium",
        "salary_min_lpa": 10.0, "salary_max_lpa": 24.0,
        "tech_stack": ["c", "c++", "autosar", "can", "linux"],
        "embedded_domains": ["automotive services", "product engineering"],
        "prep_focus": ["c/c++", "autosar", "debugging"],
    },
}

# Explicit overrides for marquee targets (partial dicts merged over tier defaults).
_OVERRIDES: dict[str, dict] = {
    "qualcomm": {"salary_min_lpa": 28.0, "salary_max_lpa": 60.0,
                 "tech_stack": ["c", "c++", "arm", "hexagon dsp", "rtos", "device driver"],
                 "embedded_domains": ["snapdragon soc", "modem", "multimedia"],
                 "prep_focus": ["c internals", "dsa", "os concepts", "arm architecture"]},
    "nvidia": {"salary_min_lpa": 30.0, "salary_max_lpa": 65.0,
               "tech_stack": ["c", "c++", "cuda", "embedded linux", "device driver"],
               "embedded_domains": ["drive platform", "tegra soc", "autonomous"],
               "prep_focus": ["c++", "dsa", "gpu/soc architecture", "linux drivers"]},
    "bosch": {"salary_min_lpa": 14.0, "salary_max_lpa": 28.0,
              "tech_stack": ["c", "autosar", "can", "iso 26262", "misra c"],
              "embedded_domains": ["automotive", "adas", "powertrain"],
              "prep_focus": ["autosar bsw", "iso 26262", "can/uds"]},
    "nxp semiconductors": {"tech_stack": ["c", "arm", "autosar", "freertos", "can-fd", "s32k"],
                           "embedded_domains": ["automotive mcu", "s32 platform"],
                           "prep_focus": ["mcu firmware", "autosar mcal", "can-fd"]},
    "texas instruments": {"tech_stack": ["c", "rtos", "spi", "i2c", "arm", "dsp"],
                          "embedded_domains": ["real-time control", "c2000", "sitara"],
                          "prep_focus": ["real-time control", "dsp", "peripherals"]},
    "intel": {"salary_min_lpa": 26.0, "salary_max_lpa": 58.0,
              "tech_stack": ["c", "c++", "linux kernel", "device driver", "pcie"],
              "embedded_domains": ["platform firmware", "bios", "soc"],
              "prep_focus": ["c/c++", "os internals", "computer architecture"]},
    "cisco": {"tech_stack": ["c", "linux kernel", "device driver", "tcp/ip", "ethernet"],
              "embedded_domains": ["network os", "routing/switching"],
              "prep_focus": ["networking", "linux internals", "dsa"]},
}


def _profile_for(target: CompanyTarget) -> CompanyProfile:
    base = dict(_TIER_DEFAULTS.get(target.tier, _TIER_DEFAULTS[CompanyTier.INDIA_FOCUSED]))
    base.update(_OVERRIDES.get(target.name.lower(), {}))
    return CompanyProfile(
        name=target.name,
        tier=target.tier.value,
        careers_url=target.careers_url,
        priority=target.priority,
        india_office=target.india_office,
        interview_rounds=base["interview_rounds"],
        interview_difficulty=base["interview_difficulty"],
        salary_min_lpa=base["salary_min_lpa"],
        salary_max_lpa=base["salary_max_lpa"],
        tech_stack=list(base["tech_stack"]),
        embedded_domains=list(base["embedded_domains"]),
        prep_focus=list(base["prep_focus"]),
    )


# Precompute all 55 profiles keyed by lowercase name.
PROFILES: dict[str, CompanyProfile] = {t.name.lower(): _profile_for(t) for t in REGISTRY}


def get_profile(name: str) -> CompanyProfile | None:
    return PROFILES.get((name or "").strip().lower())


def all_profiles() -> list[CompanyProfile]:
    return sorted(PROFILES.values(), key=lambda p: p.priority, reverse=True)
