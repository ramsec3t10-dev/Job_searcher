"""EMBEDHUNT AI — Code Intelligence Engine (Module 8).

A deterministic, dependency-free static reviewer specialised for embedded
C/C++ firmware. It flags the mistakes that repeatedly surface in embedded
interviews and code reviews (ISR safety, memory safety, MISRA-ish style) and
returns a quality score plus actionable fixes. No code is ever executed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


_WEIGHT = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 8,
    Severity.LOW: 3,
    Severity.INFO: 1,
}


@dataclass
class CodeIssue:
    line: int
    severity: Severity
    rule: str
    message: str
    suggestion: str
    snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
            "suggestion": self.suggestion,
            "snippet": self.snippet,
        }


@dataclass
class CodeReview:
    language: str
    quality_score: int
    issues: list[CodeIssue] = field(default_factory=list)
    summary: str = ""
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        by_sev: dict[str, int] = {}
        for i in self.issues:
            by_sev[i.severity.value] = by_sev.get(i.severity.value, 0) + 1
        return {
            "language": self.language,
            "quality_score": self.quality_score,
            "issue_count": len(self.issues),
            "issues_by_severity": by_sev,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "metrics": self.metrics,
        }


# (compiled_regex, severity, rule_id, message, suggestion)
_LINE_RULES: list[tuple[re.Pattern, Severity, str, str, str]] = [
    (re.compile(r"\bgets\s*\("), Severity.CRITICAL, "unsafe-gets",
     "gets() has no bounds checking and is a classic buffer-overflow vector.",
     "Use fgets(buf, sizeof(buf), stream) instead."),
    (re.compile(r"\b(strcpy|strcat|sprintf)\s*\("), Severity.HIGH, "unsafe-str",
     "Unbounded string operation can overflow the destination buffer.",
     "Use the bounded variant (strncpy/strncat/snprintf) with an explicit size."),
    (re.compile(r"\bwhile\s*\(\s*1\s*\)|\bfor\s*\(\s*;\s*;\s*\)"), Severity.LOW, "infinite-loop",
     "Infinite loop detected — ensure this is an intentional super-loop / task.",
     "Confirm a watchdog or break condition exists for non-main-loop code."),
    (re.compile(r"\bdelay\s*\(|\bHAL_Delay\s*\(|\bsleep\s*\("), Severity.MEDIUM, "blocking-delay",
     "Blocking delay stalls the CPU and is unsafe inside an ISR or RTOS-critical path.",
     "Use a non-blocking timer, RTOS delay (vTaskDelay), or a state machine."),
    (re.compile(r"\bmalloc\s*\(|\bcalloc\s*\(|\bnew\b"), Severity.MEDIUM, "dynamic-alloc",
     "Dynamic allocation on resource-constrained MCUs risks fragmentation/heap exhaustion.",
     "Prefer static/pool allocation; if unavoidable, check the return value."),
    (re.compile(r"==\s*(true|false|TRUE|FALSE)\b"), Severity.LOW, "bool-compare",
     "Explicit comparison to a boolean literal is redundant and error-prone.",
     "Write `if (flag)` / `if (!flag)` instead."),
    (re.compile(r"\bfloat\b|\bdouble\b"), Severity.INFO, "float-usage",
     "Floating-point on an FPU-less MCU is slow and unsafe inside ISRs.",
     "Prefer fixed-point arithmetic where hard-real-time or ISR context applies."),
    (re.compile(r"=\s*=\s*=|!\s*=\s*="), Severity.HIGH, "typo-operator",
     "Suspicious comparison operator.",
     "Verify the intended operator (== / != )."),
    (re.compile(r"\bstrlen\s*\([^)]*\)\s*[<>]"), Severity.LOW, "strlen-loop",
     "strlen() inside a loop condition is O(n) per iteration.",
     "Cache the length in a variable before the loop."),
]

_ASSIGN_IN_IF = re.compile(r"\bif\s*\(\s*[A-Za-z_]\w*\s*=\s*[^=]")
_ISR_HINT = re.compile(r"ISR|__interrupt|__attribute__\s*\(\s*\(\s*interrupt", re.I)
_MAGIC_NUMBER = re.compile(r"[^\w.]\b(?!0[xX])(\d{3,})\b")


class CodeIntelligenceEngine:
    def review(self, code: str, language: str = "c") -> CodeReview:
        lines = code.splitlines()
        issues: list[CodeIssue] = []
        in_isr = _ISR_HINT.search(code) is not None
        volatile_seen = "volatile" in code

        for idx, raw in enumerate(lines, start=1):
            line = self._strip_comment(raw)
            if not line.strip():
                continue

            for pattern, sev, rule, msg, fix in _LINE_RULES:
                if pattern.search(line):
                    # Only escalate blocking-delay to HIGH when in an ISR context.
                    if rule == "blocking-delay" and in_isr:
                        sev = Severity.HIGH
                    if rule == "float-usage" and not in_isr:
                        continue
                    issues.append(CodeIssue(idx, sev, rule, msg, fix, raw.strip()))

            if _ASSIGN_IN_IF.search(line):
                issues.append(CodeIssue(
                    idx, Severity.HIGH, "assign-in-condition",
                    "Assignment (=) used where a comparison (==) was likely intended.",
                    "Use == for comparison, or wrap in extra parens if assignment is deliberate.",
                    raw.strip(),
                ))

            if _MAGIC_NUMBER.search(line) and "#define" not in line and "enum" not in line:
                issues.append(CodeIssue(
                    idx, Severity.LOW, "magic-number",
                    "Magic number reduces readability and maintainability.",
                    "Extract into a named #define or const with a descriptive name.",
                    raw.strip(),
                ))

        if in_isr and not volatile_seen:
            issues.append(CodeIssue(
                0, Severity.HIGH, "missing-volatile",
                "ISR detected but no `volatile` qualifier found on any shared variable.",
                "Mark variables shared between an ISR and main context as `volatile`.",
                "",
            ))

        metrics = {
            "line_count": len(lines),
            "isr_context_detected": in_isr,
            "uses_volatile": volatile_seen,
        }
        score = self._score(issues)
        return CodeReview(
            language=language,
            quality_score=score,
            issues=sorted(issues, key=lambda i: (_WEIGHT[i.severity], i.line), reverse=True),
            summary=self._summary(score, issues),
            metrics=metrics,
        )

    def _strip_comment(self, line: str) -> str:
        # Naive single-line comment stripping (good enough for review heuristics).
        for marker in ("//", "/*"):
            pos = line.find(marker)
            if pos != -1:
                return line[:pos]
        return line

    def _score(self, issues: list[CodeIssue]) -> int:
        penalty = sum(_WEIGHT[i.severity] for i in issues)
        return max(0, 100 - penalty)

    def _summary(self, score: int, issues: list[CodeIssue]) -> str:
        crit = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in issues if i.severity == Severity.HIGH)
        if not issues:
            return "No issues detected. Clean, review-ready code."
        if crit:
            return f"{crit} critical and {high} high-severity issue(s) must be fixed before submission."
        if score >= 80:
            return "Solid code with minor style improvements suggested."
        if score >= 60:
            return "Functional but several correctness/safety concerns need attention."
        return "Significant safety and quality issues detected — refactor recommended."
