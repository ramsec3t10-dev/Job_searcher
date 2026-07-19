"""EMBEDHUNT AI — Adaptive interview engine (Module 10).

Builds balanced mock-interview sessions from the 500+ question bank, weighting
the candidate's weak skills higher, scores free-text answers against expected
keywords, and evaluates a session into a readiness score with strong/weak topic
breakdown. Deterministic and offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.interview.question_bank_extended import ALL_QUESTIONS, BY_SKILL

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are", "for",
    "with", "how", "what", "you", "your", "it", "this", "that", "when", "would",
    "do", "does", "explain", "describe", "which", "at", "as", "be", "by",
}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9+#./-]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


@dataclass
class InterviewQuestion:
    id: str
    q: str
    skill: str
    category: str
    type: str
    difficulty: str
    expected: str

    def to_dict(self, include_expected: bool = False) -> dict:
        d = {"id": self.id, "q": self.q, "skill": self.skill,
             "category": self.category, "type": self.type, "difficulty": self.difficulty}
        if include_expected:
            d["expected"] = self.expected
        return d


@dataclass
class AnswerScore:
    id: str
    skill: str
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    feedback: str = ""


@dataclass
class InterviewEvaluation:
    readiness_score: int
    answered: int
    total: int
    per_question: list[AnswerScore] = field(default_factory=list)
    strong_skills: list[str] = field(default_factory=list)
    weak_skills: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "readiness_score": self.readiness_score,
            "answered": self.answered,
            "total": self.total,
            "strong_skills": self.strong_skills,
            "weak_skills": self.weak_skills,
            "summary": self.summary,
            "per_question": [
                {"id": s.id, "skill": s.skill, "score": s.score,
                 "matched_keywords": s.matched_keywords, "feedback": s.feedback}
                for s in self.per_question
            ],
        }


def _to_question(d: dict) -> InterviewQuestion:
    return InterviewQuestion(
        id=d["id"], q=d["q"], skill=d["skill"], category=d["category"],
        type=d["type"], difficulty=d["difficulty"], expected=d.get("expected", ""),
    )


_BY_ID = {d["id"]: d for d in ALL_QUESTIONS}


class InterviewEngine:
    def build_session(self, skills: list[str], *, count: int = 10,
                      weak_skills: list[str] | None = None,
                      include_behavioral: bool = True) -> list[InterviewQuestion]:
        weak = {s.lower() for s in (weak_skills or [])}
        wanted = [s.lower() for s in skills] or list(BY_SKILL.keys())
        # weak skills first (adaptive focus), then the rest
        ordered = sorted(wanted, key=lambda s: (s not in weak, s))

        picked: list[dict] = []
        seen: set[str] = set()
        # round-robin across skills for balance
        pools = {s: [q for q in BY_SKILL.get(s, [])] for s in ordered}
        idx = 0
        while len(picked) < count and any(pools.values()):
            progressed = False
            for s in ordered:
                pool = pools.get(s)
                if not pool:
                    continue
                # weak skills contribute an extra question per round
                take = 2 if s in weak else 1
                for _ in range(take):
                    if pool and len(picked) < count:
                        q = pool.pop(0)
                        if q["id"] not in seen:
                            seen.add(q["id"])
                            picked.append(q)
                            progressed = True
            if not progressed:
                break
            idx += 1

        if include_behavioral and len(picked) < count:
            for q in BY_SKILL.get("behavioral", []):
                if len(picked) >= count:
                    break
                if q["id"] not in seen:
                    seen.add(q["id"])
                    picked.append(q)
        return [_to_question(q) for q in picked[:count]]


    # ── Realistic full-arc session ───────────────────────────────────────
    #   Mirrors a real panel: intro → warm-up → core deep-dive → coding →
    #   behavioral → your-questions. Stages reference the same flat question
    #   list used for scoring, so evaluate() works unchanged.
    def build_realistic_session(self, skills: list[str], *,
                                weak_skills: list[str] | None = None) -> dict:
        wanted = [s.lower() for s in skills] or ["c", "rtos"]
        weak = {s.lower() for s in (weak_skills or [])}

        def pick(pool: list[dict], n: int, taken: set[str]) -> list[dict]:
            out = []
            for q in pool:
                if len(out) >= n:
                    break
                if q["id"] in taken:
                    continue
                taken.add(q["id"])
                out.append(q)
            return out

        def skill_pool(types: set[str], difficulties: set[str]) -> list[dict]:
            pool: list[dict] = []
            # weak skills first so the deep-dive lands where it should
            for s in sorted(wanted, key=lambda x: (x not in weak, x)):
                for q in BY_SKILL.get(s, []):
                    if q["type"] in types and q["difficulty"] in difficulties:
                        pool.append(q)
            # curated/company-asked outrank templated filler
            pool.sort(key=lambda q: 0 if q["category"] in ("curated", "company_asked") else 1)
            return pool

        taken: set[str] = set()
        stages = [
            {"name": "introduction", "title": "Introduction",
             "brief": "Give your 90-second introduction, then walk your most recent project top-down.",
             "questions": pick(BY_SKILL.get("behavioral", []), 1, taken)
                          + pick(BY_SKILL.get("hr", []), 1, taken)},
            {"name": "warm_up", "title": "Warm-up",
             "brief": "Quick checks on the skills you claim — answer crisply.",
             "questions": pick(skill_pool({"core"}, {"easy"}), 2, taken)},
            {"name": "core_technical", "title": "Core deep-dive",
             "brief": "The heart of the interview. Reason out loud; state trade-offs.",
             "questions": pick(skill_pool({"core", "applied"}, {"medium", "hard"}), 4, taken)},
            {"name": "coding", "title": "Coding",
             "brief": "Talk while you write. State complexity without being asked.",
             "questions": pick(skill_pool({"coding"}, {"easy", "medium", "hard"}), 2, taken)},
            {"name": "behavioral", "title": "Behavioral",
             "brief": "STAR structure: your role, your decisions, a measurable result.",
             "questions": pick(BY_SKILL.get("behavioral", [])[1:], 2, taken)},
            {"name": "your_questions", "title": "Your questions",
             "brief": "Ask two real questions about the team's technology and process.",
             "questions": []},
        ]
        flat = [q for st in stages for q in st["questions"]]
        return {
            "stages": [
                {"name": st["name"], "title": st["title"], "brief": st["brief"],
                 "question_ids": [q["id"] for q in st["questions"]]}
                for st in stages
            ],
            "questions": [_to_question(q) for q in flat],
        }

    def score_answer(self, question_id: str, answer: str) -> AnswerScore:
        q = _BY_ID.get(question_id)
        if q is None:
            return AnswerScore(id=question_id, skill="", score=0, feedback="Unknown question.")
        expected_kw = _keywords(q.get("expected", "")) | _keywords(q["skill"])
        answer_kw = _keywords(answer)
        if not answer_kw:
            return AnswerScore(id=question_id, skill=q["skill"], score=0,
                               feedback="No answer provided.")
        if not expected_kw:
            # behavioural/HR: score on substance (length/structure) rather than keywords
            score = min(100, 40 + len(answer_kw) * 4)
            return AnswerScore(id=question_id, skill=q["skill"], score=score,
                               feedback="Structured, detailed answers score higher.")
        matched = sorted(expected_kw & answer_kw)
        coverage = len(matched) / len(expected_kw)
        length_bonus = min(0.2, len(answer_kw) / 100)
        score = int(round(min(1.0, coverage + length_bonus) * 100))
        return AnswerScore(id=question_id, skill=q["skill"], score=score,
                           matched_keywords=matched,
                           feedback=self._feedback(score, expected_kw - answer_kw))

    def evaluate(self, answers: dict[str, str], *, total: int | None = None) -> InterviewEvaluation:
        scores = [self.score_answer(qid, ans) for qid, ans in answers.items()]
        answered = sum(1 for s in scores if s.score > 0)
        total = total or len(answers)
        by_skill: dict[str, list[int]] = {}
        for s in scores:
            by_skill.setdefault(s.skill, []).append(s.score)
        strong = sorted(k for k, v in by_skill.items() if sum(v) / len(v) >= 70)
        weak = sorted(k for k, v in by_skill.items() if sum(v) / len(v) < 50)
        readiness = int(round(sum(s.score for s in scores) / total)) if total else 0
        readiness = max(0, min(100, readiness))
        summary = (f"Readiness {readiness}/100 over {answered}/{total} answered. "
                   f"Strong: {', '.join(strong) or 'n/a'}. Focus: {', '.join(weak) or 'n/a'}.")
        return InterviewEvaluation(
            readiness_score=readiness, answered=answered, total=total,
            per_question=scores, strong_skills=strong, weak_skills=weak, summary=summary,
        )

    @staticmethod
    def _feedback(score: int, missing: set[str]) -> str:
        if score >= 80:
            return "Strong answer."
        if score >= 50:
            hint = ", ".join(sorted(missing)[:4])
            return f"Good, but also mention: {hint}." if hint else "Good answer."
        hint = ", ".join(sorted(missing)[:5])
        return f"Incomplete — cover key points: {hint}." if hint else "Answer lacks depth."


_default: InterviewEngine | None = None


def get_interview_engine() -> InterviewEngine:
    global _default
    if _default is None:
        _default = InterviewEngine()
    return _default
