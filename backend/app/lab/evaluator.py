"""EMBEDHUNT AI — Coding Lab evaluator (Module 7).

Grades a submission statically, three layers deep:
  1. concept coverage against the challenge's required concepts,
  2. anti-pattern detection — the classic mistakes interviewers screen for,
  3. a Code Intelligence safety/quality review.

Code is never executed on the server (no sandbox), which is called out in the
result. After grading, the response includes the reference solution and the
interviewer's notes — the submission is a training rep, not an exam.
"""
from __future__ import annotations

import re

from app.ai.code_intelligence import CodeIntelligenceEngine
from app.lab.challenges import Challenge


class LabEvaluator:
    def __init__(self):
        self.reviewer = CodeIntelligenceEngine()

    def evaluate(self, challenge: Challenge, code: str) -> dict:
        lowered = code.lower()
        present = [c for c in challenge.required_concepts if c in lowered]
        missing = [c for c in challenge.required_concepts if c not in lowered]
        coverage = int(len(present) / len(challenge.required_concepts) * 100) if challenge.required_concepts else 0

        # The mistakes a real interviewer would call out.
        warnings = [
            message
            for pattern, message in challenge.anti_patterns
            if re.search(pattern, code, re.IGNORECASE)
        ]

        still_todo = "todo" in lowered or "// todo" in lowered
        review = self.reviewer.review(code, "c")

        # Combined score: concept coverage (60%) + static quality (40%),
        # minus 8 points per flagged anti-pattern.
        score = int(coverage * 0.6 + review.quality_score * 0.4)
        score = max(0, score - 8 * len(warnings))
        passed = coverage >= 80 and not still_todo and not warnings and score >= 65

        return {
            "challenge_id": challenge.id,
            "passed": passed,
            "score": score,
            "concept_coverage": coverage,
            "concepts_present": present,
            "concepts_missing": missing,
            "anti_patterns_flagged": warnings,
            "static_review": review.to_dict(),
            "feedback": self._feedback(passed, coverage, missing, warnings, still_todo),
            # Training payload: every submission ends with the model answer.
            "reference_solution": challenge.reference_solution,
            "interview_notes": challenge.interview_notes,
            "note": "Static grading only — code is not executed on the server.",
        }

    def _feedback(self, passed: bool, coverage: int, missing: list[str],
                  warnings: list[str], still_todo: bool) -> str:
        if still_todo:
            return "Your submission still contains a TODO placeholder — complete the implementation."
        if warnings:
            return ("An interviewer would stop you here: " + " ".join(warnings[:2]) +
                    " Compare your approach with the reference solution below.")
        if passed:
            return (f"Solid — {coverage}% concept coverage and no red flags. "
                    "Now read the interview notes: they tell you what a strong "
                    "candidate says OUT LOUD while writing this.")
        if missing:
            return (f"Missing expected constructs: {', '.join(missing)}. "
                    "Revisit the prompt and hints, then study the reference solution.")
        return "Close — address the static-review issues, then compare with the reference."
