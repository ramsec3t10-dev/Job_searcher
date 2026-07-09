"""EMBEDHUNT AI — Skill extractor with confidence scoring.

Extends the base resume taxonomy to 300+ embedded/software skills and assigns a
0-1 confidence to each detected skill from evidence signals (mention frequency,
presence in a dedicated skills section, and proximity to experience/duration
phrases). Deterministic and offline.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from app.resume.extractor import (
    ALIASES as _BASE_ALIASES,
    AUTOMOTIVE as _B_AUTO,
    CONCEPTS as _B_CONC,
    HARDWARE as _B_HW,
    PROGRAMMING as _B_PROG,
    PROTOCOLS as _B_PROTO,
    RTOS_OS as _B_RTOS,
    TOOLS as _B_TOOLS,
)

# ── Extended taxonomy (union with base ⇒ 300+ unique skills) ──────────────────
_E_PROG = {
    "c#", "go", "golang", "javascript", "typescript", "perl", "bash", "shell",
    "lua", "objective-c", "swift", "systemverilog", "tcl", "scala", "r",
    "embedded c", "sql", "labview",
}
_E_RTOS = {
    "ucos", "uc/os", "mbed os", "nucleus", "integrity", "sysbios", "windows ce",
    "android", "posix", "rtems", "chibios", "nuttx", "azure rtos", "keil rtx",
}
_E_PROTO = {
    "lora", "lorawan", "nfc", "rs232", "rs485", "profibus", "profinet",
    "ethercat", "j1939", "obd-ii", "coap", "http", "https", "websocket",
    "gpio", "pwm", "adc", "dac", "sent", "psi5", "a2b", "mipi", "sdio",
    "qspi", "onewire", "1-wire", "smbus", "sercos", "canopen",
}
_E_HW = {
    "cortex-m0", "cortex-m3", "esp8266", "nrf52", "msp430", "altera", "xilinx",
    "zynq", "raspberry pi", "beaglebone", "arduino", "atmega", "imx", "tegra",
    "dsp", "microcontroller", "microprocessor", "soc", "pcb", "schematic",
    "altium", "kicad", "sam", "kinetis", "lpc", "efm32", "gd32", "am335x",
    "jetson", "ecu hardware", "power electronics", "sensors", "actuators",
}
_E_AUTO = {
    "asil-a", "asil-c", "iso 21448", "classic autosar", "adaptive autosar",
    "mcal", "com stack", "diagnostics", "obd", "aspice", "automotive spice",
    "iso 14229", "iso 11898", "dbc", "canoe", "canalyzer", "vector tools",
    "ecu", "tara", "iso 21434", "vehicle networks", "j1939 stack", "xcp", "ccp",
}
_E_TOOLS = {
    "logic analyzer", "meson", "ninja", "kubernetes", "perforce", "confluence",
    "cppunit", "unity test", "ceedling", "sonarqube", "valgrind", "keil",
    "iar", "iar embedded workbench", "mplab", "code composer studio", "eclipse",
    "vs code", "doxygen", "gitlab", "github actions", "bazel", "clang", "gcc",
    "llvm", "segger", "j-link", "ozone", "ldra", "vectorcast", "tessy",
    "matlab simulink", "targetlink", "ansys", "canoe.diva",
}
_E_CONC = {
    "isr", "mpu", "low power", "dfu", "hsm", "watchdog", "semaphore", "mutex",
    "spinlock", "scheduling", "multithreading", "concurrency", "design patterns",
    "oop", "data structures", "algorithms", "memory mapped io", "endianness",
    "fixed point", "dsp algorithms", "kalman filter", "sensor fusion",
    "control systems", "real-time", "hard real-time", "timing analysis", "wcet",
    "code coverage", "unit testing", "integration testing", "hil", "sil", "mil",
    "model based design", "tdd", "continuous integration", "static analysis",
    "code review", "debugging", "profiling", "linker script", "startup code",
    "flash programming", "firmware update", "communication stack",
}

TAXONOMY: dict[str, set[str]] = {
    "programming": _B_PROG | _E_PROG,
    "rtos_os": _B_RTOS | _E_RTOS,
    "protocols": _B_PROTO | _E_PROTO,
    "hardware": _B_HW | _E_HW,
    "automotive": _B_AUTO | _E_AUTO,
    "tools": _B_TOOLS | _E_TOOLS,
    "concepts": _B_CONC | _E_CONC,
}

ALL_SKILLS: set[str] = set().union(*TAXONOMY.values())
_SKILL_CATEGORY: dict[str, str] = {}
for _cat, _skills in TAXONOMY.items():
    for _s in _skills:
        _SKILL_CATEGORY.setdefault(_s.strip(), _cat)

ALIASES = {
    **_BASE_ALIASES,
    "golang": "go", "uc/os": "ucos", "1-wire": "onewire", "obd ii": "obd-ii",
    "j link": "j-link", "iar embedded workbench": "iar",
    "code composer studio": "code composer studio",
}

_SKILLS_HEADER = re.compile(
    r"(technical\s+skills|core\s+competenc|skills?\s*[:&]|technologies|tech\s+stack|expertise)",
    re.I,
)
_EXPERIENCE_NEAR = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", re.I)
_SECTION_BREAK = re.compile(r"^\s*(experience|education|projects?|summary|profile|work\s+history)\b", re.I)


@dataclass
class ExtractedSkill:
    name: str
    category: str
    confidence: float
    mentions: int
    in_skills_section: bool = False
    near_experience: bool = False
    evidence: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").lower().strip())
    for alias, canon in ALIASES.items():
        t = t.replace(alias, canon)
    return t


def _skill_pattern(skill: str) -> re.Pattern:
    esc = re.escape(skill)
    if len(skill) <= 2 and skill.isalpha():
        return re.compile(rf"\b{esc}\b")
    if skill[0].isalnum() and skill[-1].isalnum():
        return re.compile(rf"\b{esc}\b")
    return re.compile(rf"(?<![a-zA-Z0-9]){esc}(?![a-zA-Z0-9])")


def _skills_section_text(raw_text: str) -> str:
    """Return the text belonging to a skills/technical section, if present."""
    lines = raw_text.split("\n")
    collecting = False
    out: list[str] = []
    for line in lines:
        if _SKILLS_HEADER.search(line):
            collecting = True
            out.append(line)
            continue
        if collecting and _SECTION_BREAK.match(line.strip()):
            break
        if collecting:
            out.append(line)
    return "\n".join(out)


class SkillExtractor:
    """Detects skills and scores confidence from resume/job text."""

    def extract(self, raw_text: str) -> list[ExtractedSkill]:
        if not raw_text:
            return []
        full = _normalize(raw_text)
        section = _normalize(_skills_section_text(raw_text))
        near_exp_window = self._experience_terms(raw_text)

        results: list[ExtractedSkill] = []
        for skill in ALL_SKILLS:
            pat = _skill_pattern(skill)
            mentions = len(pat.findall(full))
            if mentions == 0:
                continue
            in_section = bool(section) and bool(pat.search(section))
            near_exp = skill in near_exp_window
            conf, evidence = self._confidence(mentions, in_section, near_exp)
            results.append(ExtractedSkill(
                name=skill,
                category=_SKILL_CATEGORY.get(skill, "concepts"),
                confidence=conf,
                mentions=mentions,
                in_skills_section=in_section,
                near_experience=near_exp,
                evidence=evidence,
            ))
        results.sort(key=lambda s: (-s.confidence, s.name))
        return results

    def extract_grouped(self, raw_text: str) -> dict[str, list[ExtractedSkill]]:
        grouped: dict[str, list[ExtractedSkill]] = {c: [] for c in TAXONOMY}
        for s in self.extract(raw_text):
            grouped[s.category].append(s)
        return grouped

    async def extract_ai(self, raw_text: str, *, db, user_id: str) -> list[ExtractedSkill]:
        """Regex extraction unioned with LLM-inferred skills outside the taxonomy.

        Deterministic regex hits are always kept. AI-discovered skills that the
        taxonomy missed (new tech, aliases, inferred) are appended with a
        confidence-weighted score. Any failure or the master toggle being off
        returns the deterministic list unchanged.
        """
        from app.config.logging import get_logger
        from app.config.settings import settings

        logger = get_logger(__name__)
        base = self.extract(raw_text)
        if not settings.LLM_ENRICHMENT_ENABLED:
            logger.info("skill_extractor_path", path="fallback", reason="disabled")
            return base
        try:
            from app.agents.resume_agent import ResumeAgent

            parsed = await asyncio.wait_for(
                ResumeAgent(db).parse(raw_text, user_id),
                timeout=settings.LLM_ENRICHMENT_TIMEOUT_SECONDS,
            )
            known = {s.name.lower() for s in base}
            added = 0
            for name in (parsed.skills or []):
                key = (name or "").strip().lower()
                if not key or key in known:
                    continue
                known.add(key)
                base.append(ExtractedSkill(
                    name=key,
                    category=_SKILL_CATEGORY.get(key, "concepts"),
                    confidence=0.5,  # AI-inferred, not evidence-scored
                    mentions=0,
                    in_skills_section=False,
                    near_experience=False,
                    evidence=["ai_inferred"],
                ))
                added += 1
            base.sort(key=lambda s: (-s.confidence, s.name))
            logger.info("skill_extractor_path", path="ai_enriched", ai_added=added)
        except Exception as e:  # noqa: BLE001 — enrichment must never break the caller
            logger.warning("ai_enrichment_failed", module=__name__, error=str(e))
            return self.extract(raw_text)
        return base

    @staticmethod
    def _experience_terms(raw_text: str) -> set[str]:
        """Skills that appear within ~40 chars of a 'N years' phrase."""
        text = _normalize(raw_text)
        near: set[str] = set()
        for m in _EXPERIENCE_NEAR.finditer(text):
            window = text[max(0, m.start() - 40): m.end() + 40]
            for skill in ALL_SKILLS:
                if _skill_pattern(skill).search(window):
                    near.add(skill)
        return near

    @staticmethod
    def _confidence(mentions: int, in_section: bool, near_exp: bool) -> tuple[float, list[str]]:
        evidence: list[str] = [f"{mentions} mention(s)"]
        conf = 0.45 + 0.12 * min(mentions - 1, 3)  # 0.45 → 0.81 by 4 mentions
        if in_section:
            conf += 0.25
            evidence.append("skills section")
        if near_exp:
            conf += 0.15
            evidence.append("near experience")
        return round(max(0.0, min(1.0, conf)), 3), evidence


_default_extractor: SkillExtractor | None = None


def get_skill_extractor() -> SkillExtractor:
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = SkillExtractor()
    return _default_extractor
