"""EMBEDHUNT AI — Coding Lab evaluator (Module 7).

Grades a submission statically: concept coverage against the challenge's
required concepts plus a Code Intelligence safety/quality review. Code is
never executed on the server (no sandbox), which is called out in the result.
"""
from __future__ import annotations

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

        still_todo = "todo" in lowered or "// todo" in lowered
        review = self.reviewer.review(code, "c")

        # Combined score: concept coverage (60%) + static quality (40%).
        score = int(coverage * 0.6 + review.quality_score * 0.4)
        passed = coverage >= 80 and not still_todo and score >= 65

        return {
            "challenge_id": challenge.id,
            "passed": passed,
            "score": score,
            "concept_coverage": coverage,
            "concepts_present": present,
            "concepts_missing": missing,
            "static_review": review.to_dict(),
            "feedback": self._feedback(passed, coverage, missing, still_todo),
            "note": "Static grading only — code is not executed on the server.",
        }

    def _feedback(self, passed: bool, coverage: int, missing: list[str], still_todo: bool) -> str:
        if still_todo:
            return "Your submission still contains a TODO placeholder — complete the implementation."
        if passed:
            return f"Nice work — {coverage}% concept coverage and no blocking issues."
        if missing:
            return f"Missing expected constructs: {', '.join(missing)}. Revisit the prompt and hints."
        return "Close — address the static-review issues to pass."
