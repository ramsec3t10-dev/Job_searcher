"""EMBEDHUNT AI — Extended interview question bank (500+ questions).

Combines three layers:
  1. Curated, hand-written questions (the original ``question_bank.QUESTIONS``
     plus expert additions) — highest quality, used first.
  2. Systematic per-skill coverage generated from six well-formed templates over
     a curated set of interview-relevant embedded skills, guaranteeing breadth
     and a 500+ total.
  3. Behavioural, HR, and system-design questions.

Everything is deterministic and offline. Each question is a dict with keys:
``id, q, skill, category, type, difficulty, expected``.
"""
from __future__ import annotations

from app.interview.question_bank import QUESTIONS as _CURATED_BY_SKILL

# ── Curated additions (distinct, real questions) ─────────────────────────────
_CURATED_EXTRA: list[dict] = [
    {"q": "How does a watchdog timer improve system reliability, and how do you service it safely?", "skill": "watchdog", "type": "core", "difficulty": "medium", "expected": "Detects hangs, reset; kick only when main loop healthy"},
    {"q": "Explain the boot sequence from reset vector to main() on a Cortex-M.", "skill": "bootloader", "type": "core", "difficulty": "hard", "expected": "Reset handler, .data/.bss init, vector table, SystemInit, main"},
    {"q": "How do you place code/data in specific memory regions using a linker script?", "skill": "linker script", "type": "core", "difficulty": "hard", "expected": "Sections, MEMORY/SECTIONS, attributes, __attribute__((section))"},
    {"q": "What causes stack corruption and how do you detect it at runtime?", "skill": "memory management", "type": "core", "difficulty": "hard", "expected": "Overflow into adjacent region; canaries, MPU, high-water marks"},
    {"q": "Describe how DMA offloads the CPU and the coherency issues it introduces.", "skill": "dma", "type": "core", "difficulty": "hard", "expected": "Peripheral<->memory without CPU; cache invalidate/clean, alignment"},
    {"q": "How would you debounce a mechanical button in firmware?", "skill": "gpio", "type": "applied", "difficulty": "easy", "expected": "Sampling + time filter or RC + Schmitt trigger"},
    {"q": "Explain how an interrupt service routine should be written for minimal latency.", "skill": "interrupt", "type": "core", "difficulty": "medium", "expected": "Short, no blocking, defer work, volatile flags, clear source"},
    {"q": "What is the difference between a semaphore and a mutex regarding ownership?", "skill": "mutex", "type": "core", "difficulty": "medium", "expected": "Mutex has owner + priority inheritance; semaphore is a counter"},
    {"q": "How do you achieve low-power operation on a battery device?", "skill": "low power", "type": "applied", "difficulty": "medium", "expected": "Sleep modes, clock gating, duty cycling, peripheral power-down"},
    {"q": "Explain secure boot and the chain of trust.", "skill": "secure boot", "type": "core", "difficulty": "hard", "expected": "Immutable root, signature verification at each stage"},
    {"q": "How does an OTA firmware update remain robust against power loss?", "skill": "ota", "type": "applied", "difficulty": "hard", "expected": "A/B banks, rollback, CRC/signature, atomic switch"},
    {"q": "Describe fixed-point arithmetic and when you'd use it over floating point.", "skill": "fixed point", "type": "core", "difficulty": "medium", "expected": "Integer scaling; no FPU, deterministic, faster"},
    {"q": "What is endianness and how does it affect protocol parsing?", "skill": "endianness", "type": "core", "difficulty": "medium", "expected": "Byte order; convert with htons/ntohl, define wire format"},
    {"q": "How do you write a portable state machine in C?", "skill": "state machine", "type": "coding", "difficulty": "medium", "expected": "Enum states + transition table or switch, event-driven"},
    {"q": "Explain UART framing errors and their common causes.", "skill": "uart", "type": "core", "difficulty": "medium", "expected": "Baud mismatch, noise, wrong stop bits; check config/clock"},
    {"q": "What are the trade-offs of using an RTOS vs a bare-metal super-loop?", "skill": "bare metal", "type": "core", "difficulty": "medium", "expected": "Determinism/complexity vs simplicity/footprint"},
    {"q": "How do you validate timing requirements (WCET) in a real-time system?", "skill": "wcet", "type": "core", "difficulty": "hard", "expected": "Static analysis, measurement, scheduling analysis"},
    {"q": "Explain MISRA C and why it is used in safety-critical firmware.", "skill": "misra c", "type": "core", "difficulty": "medium", "expected": "Coding guidelines reducing undefined/implementation-defined behavior"},
    {"q": "How does CAN error handling (error frames, bus-off) work?", "skill": "can", "type": "core", "difficulty": "hard", "expected": "TEC/REC counters, error-active/passive, bus-off recovery"},
    {"q": "Describe how you would bring up a new custom board.", "skill": "bsp", "type": "applied", "difficulty": "hard", "expected": "Clocks, power, JTAG, blink LED, UART, then peripherals"},
]

# ── Systematic coverage: curated interview-relevant skills × templates ────────
_CORE_SKILLS: list[tuple[str, str]] = [
    ("c", "programming"), ("c++", "programming"), ("python", "programming"),
    ("rust", "programming"), ("assembly", "programming"), ("embedded c", "programming"),
    ("freertos", "rtos_os"), ("rtos", "rtos_os"), ("zephyr", "rtos_os"),
    ("threadx", "rtos_os"), ("linux", "rtos_os"), ("embedded linux", "rtos_os"),
    ("yocto", "rtos_os"), ("bare metal", "rtos_os"), ("posix", "rtos_os"),
    ("can", "protocols"), ("can-fd", "protocols"), ("lin", "protocols"),
    ("spi", "protocols"), ("i2c", "protocols"), ("uart", "protocols"),
    ("usb", "protocols"), ("ethernet", "protocols"), ("tcp/ip", "protocols"),
    ("mqtt", "protocols"), ("modbus", "protocols"), ("ble", "protocols"),
    ("uds", "protocols"), ("someip", "protocols"), ("flexray", "protocols"),
    ("arm", "hardware"), ("cortex-m", "hardware"), ("cortex-a", "hardware"),
    ("risc-v", "hardware"), ("stm32", "hardware"), ("esp32", "hardware"),
    ("fpga", "hardware"), ("dsp", "hardware"), ("soc", "hardware"),
    ("microcontroller", "hardware"), ("sensors", "hardware"),
    ("autosar", "automotive"), ("iso 26262", "automotive"), ("asil", "automotive"),
    ("adas", "automotive"), ("functional safety", "automotive"), ("mcal", "automotive"),
    ("diagnostics", "automotive"), ("aspice", "automotive"),
    ("jtag", "tools"), ("gdb", "tools"), ("cmake", "tools"), ("git", "tools"),
    ("docker", "tools"), ("trace32", "tools"), ("valgrind", "tools"),
    ("gtest", "tools"), ("static analysis", "tools"),
    ("device driver", "concepts"), ("bootloader", "concepts"), ("dma", "concepts"),
    ("interrupt", "concepts"), ("mmu", "concepts"), ("power management", "concepts"),
    ("state machine", "concepts"), ("watchdog", "concepts"), ("mutex", "concepts"),
    ("multithreading", "concepts"), ("design patterns", "concepts"),
    ("data structures", "concepts"), ("algorithms", "concepts"),
    ("unit testing", "concepts"), ("code coverage", "concepts"),
    ("real-time", "concepts"), ("sensor fusion", "concepts"),
]

# (template, type, difficulty, expected-hint)
_TEMPLATES: list[tuple[str, str, str, str]] = [
    ("Explain the fundamentals of {S} and where it is used in embedded systems.",
     "core", "medium", "Definition, mechanism, and typical embedded use-cases of {S}."),
    ("What are the key trade-offs and constraints when using {S} on resource-constrained hardware?",
     "core", "hard", "Memory/CPU/power/timing trade-offs specific to {S}."),
    ("Walk through how you would debug a problem involving {S} in a production system.",
     "applied", "hard", "Reproduce, instrument, isolate, tooling and root-cause approach for {S}."),
    ("What are best practices for testing and validating {S}?",
     "core", "medium", "Test strategy, edge cases, and verification methods for {S}."),
    ("When would you choose {S} over an alternative, and what drives that decision?",
     "core", "medium", "Selection criteria and comparison for {S}."),
    ("Describe a project where {S} was central and the biggest lesson you learned.",
     "behavioral", "easy", "Concrete scenario, your role, outcome, and learning around {S}."),
]

# ── Behavioural / HR / system design ─────────────────────────────────────────
_BEHAVIORAL: list[dict] = [
    {"q": "Tell me about a time you found a difficult bug under deadline pressure.", "difficulty": "medium"},
    {"q": "Describe a disagreement with a teammate over a technical decision and how you resolved it.", "difficulty": "medium"},
    {"q": "Tell me about a project that failed and what you took away from it.", "difficulty": "medium"},
    {"q": "How do you handle a requirement change late in a release cycle?", "difficulty": "medium"},
    {"q": "Describe a time you improved a process or tool for your team.", "difficulty": "easy"},
    {"q": "How do you prioritise when everything is 'urgent'?", "difficulty": "easy"},
    {"q": "Tell me about mentoring a junior engineer.", "difficulty": "easy"},
    {"q": "Describe the most complex system you have worked on end to end.", "difficulty": "hard"},
    {"q": "How do you keep your embedded skills current?", "difficulty": "easy"},
    {"q": "Tell me about a time you pushed back on scope to protect quality.", "difficulty": "medium"},
]
_HR: list[dict] = [
    {"q": "Why do you want to join this company specifically?", "difficulty": "easy"},
    {"q": "Where do you see your embedded career in five years?", "difficulty": "easy"},
    {"q": "What are your salary expectations and how did you arrive at them?", "difficulty": "medium"},
    {"q": "Why are you leaving your current role?", "difficulty": "easy"},
    {"q": "What kind of work environment helps you do your best work?", "difficulty": "easy"},
    {"q": "How do you handle feedback and code review criticism?", "difficulty": "easy"},
]
_SYSTEM_DESIGN: list[dict] = [
    {"q": "Design the firmware architecture for a battery-powered IoT sensor node.", "difficulty": "hard"},
    {"q": "Design an OTA update system for a fleet of automotive ECUs.", "difficulty": "hard"},
    {"q": "Design a real-time data logger that must never lose data on power loss.", "difficulty": "hard"},
    {"q": "Design the software stack for a motor-control unit with a safety requirement.", "difficulty": "hard"},
    {"q": "Design a communication protocol between two microcontrollers over a noisy link.", "difficulty": "hard"},
    {"q": "Design a bootloader supporting secure, resumable firmware updates.", "difficulty": "hard"},
    {"q": "Design a sensor-fusion pipeline for an ADAS feature.", "difficulty": "hard"},
    {"q": "Design a test harness for hardware-in-the-loop validation.", "difficulty": "hard"},
]


def _build() -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def _add(q: str, skill: str, category: str, qtype: str, difficulty: str, expected: str) -> None:
        key = q.strip().lower()
        if key in seen:
            return
        seen.add(key)
        out.append({
            "id": f"q{len(out) + 1:04d}",
            "q": q, "skill": skill, "category": category,
            "type": qtype, "difficulty": difficulty, "expected": expected,
        })

    # 1. curated (original bank)
    for skill, items in _CURATED_BY_SKILL.items():
        for it in items:
            _add(it["q"], skill, "curated", it.get("type", "core"),
                 it.get("difficulty", "medium"), it.get("expected", ""))
    # curated extras
    for it in _CURATED_EXTRA:
        _add(it["q"], it["skill"], "curated", it.get("type", "core"),
             it.get("difficulty", "medium"), it.get("expected", ""))

    # 2. templated coverage
    for skill, category in _CORE_SKILLS:
        label = skill.upper() if len(skill) <= 4 else skill
        for template, qtype, difficulty, hint in _TEMPLATES:
            _add(template.format(S=label), skill, category, qtype, difficulty,
                 hint.format(S=label))

    # 3. behavioural / HR / system design
    for it in _BEHAVIORAL:
        _add(it["q"], "behavioral", "behavioral", "behavioral", it["difficulty"],
             "STAR: situation, task, action, result.")
    for it in _HR:
        _add(it["q"], "hr", "hr", "hr", it["difficulty"], "Honest, structured, company-aligned answer.")
    for it in _SYSTEM_DESIGN:
        _add(it["q"], "system design", "system_design", "system_design", it["difficulty"],
             "Requirements, constraints, components, trade-offs, failure modes.")
    return out


ALL_QUESTIONS: list[dict] = _build()

# Indexes
BY_SKILL: dict[str, list[dict]] = {}
for _q in ALL_QUESTIONS:
    BY_SKILL.setdefault(_q["skill"], []).append(_q)


def count() -> int:
    return len(ALL_QUESTIONS)


def questions_for_skill(skill: str) -> list[dict]:
    return BY_SKILL.get(skill.lower(), [])
