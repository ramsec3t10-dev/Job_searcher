"""EMBEDHUNT AI — Context Builder.

Assembles compact, budget-bounded context payloads for each AI task from a
candidate's Career Twin and long-term memory. The Career Twin stores skills in
an *expanded* shape; this module is the single place that compacts them to the
lightweight ``{n, c, d, y, r}`` form the LLM prompts expect.

Every builder returns a plain ``dict`` whose combined content never exceeds
``MAX_CONTEXT_TOKENS`` (4000) so prompts stay cheap and within budget.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from app.llm.token_manager import (
    build_context_within_budget,
    compress_text,
    estimate_tokens,
)

MAX_CONTEXT_TOKENS = 4000
_SUMMARY_MAX_CHARS = 2000


class ContextBuilder:
    """Static builders — one per AI task. All output is token-bounded."""

    # ── Cross-user isolation guard ──────────────────────────────────────
    @staticmethod
    def _assert_owner(twin: Any, user_id: Optional[str]) -> None:
        """Fail closed if a Career Twin is about to be used for the wrong user.

        Prevents cross-user data leakage: a twin loaded for user A must never be
        assembled into context for user B. No-op when ``user_id`` is not supplied
        (internal/anonymous calls) or the twin carries no owner id.
        """
        if user_id is None or twin is None:
            return
        owner = getattr(twin, "user_id", None)
        assert owner == user_id, (
            f"career twin owner mismatch: twin belongs to {owner!r}, requested by {user_id!r}"
        )

    # ── Skill compaction ────────────────────────────────────────────────
    @staticmethod
    def _compact_skills(twin: Any) -> list[dict]:
        """Expanded skill dicts -> compact ``{n, c, d, y, r}`` form."""
        compact = []
        for s in (getattr(twin, "skills", None) or []):
            compact.append({
                "n": s.get("name", ""),
                "c": round(float(s.get("confidence", 0.0) or 0.0), 2),
                "d": s.get("depth", ""),
                "y": s.get("years_used", 0),
                "r": round(float(s.get("recency_score", 0.0) or 0.0), 2),
            })
        return compact

    @staticmethod
    def _candidate_summary(twin: Any) -> str:
        """A <=2000 char JSON snapshot of who the candidate is."""
        skills = ContextBuilder._compact_skills(twin)
        summary = {
            "role": getattr(twin, "current_role", "") or "",
            "level": getattr(twin, "career_level", "") or "",
            "years": getattr(twin, "total_years_experience", 0) or 0,
            "top_skills": [s["n"] for s in skills[:15]],
            "strengths": (getattr(twin, "strengths", None) or [])[:5],
            "weaknesses": (getattr(twin, "known_weaknesses", None) or [])[:5],
            "domain_score": getattr(twin, "embedded_domain_score", 0) or 0,
        }
        text = json.dumps(summary, separators=(",", ":"))
        if len(text) > _SUMMARY_MAX_CHARS:
            summary["top_skills"] = summary["top_skills"][:8]
            text = json.dumps(summary, separators=(",", ":"))[:_SUMMARY_MAX_CHARS]
        return text

    # ── Budget guard ────────────────────────────────────────────────────
    @staticmethod
    def _enforce_budget(payload: dict, budget: int = MAX_CONTEXT_TOKENS) -> dict:
        """Compress the largest string fields until the payload fits ``budget``."""
        def total() -> int:
            return sum(
                estimate_tokens(v if isinstance(v, str) else json.dumps(v))
                for v in payload.values()
            )

        # Iteratively halve the biggest string field until within budget.
        while total() > budget:
            str_fields = {k: v for k, v in payload.items() if isinstance(v, str) and v}
            if not str_fields:
                break
            biggest = max(str_fields, key=lambda k: estimate_tokens(str_fields[k]))
            target = max(1, estimate_tokens(payload[biggest]) // 2)
            payload[biggest] = compress_text(payload[biggest], target)
        return payload

    # ── Task builders ───────────────────────────────────────────────────
    @staticmethod
    def for_resume_analysis(resume_text: str, job_description: str = "") -> dict:
        payload = {
            "resume_text": resume_text or "",
            "job_description": job_description or "",
        }
        return ContextBuilder._enforce_budget(payload)

    @staticmethod
    def for_job_matching(twin: Any, job: dict, user_id: Optional[str] = None) -> dict:
        ContextBuilder._assert_owner(twin, user_id)
        payload = {
            "candidate_summary": ContextBuilder._candidate_summary(twin),
            "skills": [s["n"] for s in ContextBuilder._compact_skills(twin)],
            "experience_years": getattr(twin, "total_years_experience", 0) or 0,
            "current_role": getattr(twin, "current_role", "") or "",
            "job_title": job.get("title", "") or "",
            "job_description": job.get("description", "") or "",
            "job_required_skills": job.get("required_skills", []) or [],
        }
        return ContextBuilder._enforce_budget(payload)

    @staticmethod
    def for_career_mentor(twin: Any, memories: list, user_message: str, user_id: Optional[str] = None) -> dict:
        ContextBuilder._assert_owner(twin, user_id)
        components = [
            (f"memory_{i}", getattr(m, "summary", "") or "", getattr(m, "importance_score", 3) or 3)
            for i, m in enumerate(memories or [])
        ]
        recent_history = build_context_within_budget(components, budget=1500)
        payload = {
            "candidate_context": ContextBuilder._candidate_summary(twin),
            "recent_history": recent_history,
            "user_message": user_message or "",
        }
        return ContextBuilder._enforce_budget(payload)

    @staticmethod
    def for_interview(twin: Any, job: dict, skill: str = "", user_id: Optional[str] = None) -> dict:
        ContextBuilder._assert_owner(twin, user_id)
        history = getattr(twin, "interview_history", None) or []
        previous_scores = [h.get("score") for h in history if isinstance(h, dict) and "score" in h]
        payload = {
            "candidate_level": getattr(twin, "career_level", "") or "",
            "skill": skill or "",
            "job_title": job.get("title", "") or "",
            "company": job.get("company", "") or "",
            "known_weaknesses": (getattr(twin, "known_weaknesses", None) or [])[:5],
            "previous_scores": previous_scores[-5:],
        }
        return ContextBuilder._enforce_budget(payload)

    @staticmethod
    def for_roadmap(twin: Any, target_job: dict, hours_per_week: int = 10, user_id: Optional[str] = None) -> dict:
        ContextBuilder._assert_owner(twin, user_id)
        current = [s["n"] for s in ContextBuilder._compact_skills(twin)]
        required = target_job.get("required_skills", []) or []
        have = {c.lower() for c in current}
        missing = [s for s in required if s.lower() not in have]
        payload = {
            "current_skills": current,
            "missing_skills": missing,
            "target_role": target_job.get("title", "") or "",
            "experience_level": getattr(twin, "career_level", "") or "",
            "hours_per_week": hours_per_week,
            "learning_velocity": getattr(twin, "learning_velocity", 0.0) or 0.0,
        }
        return ContextBuilder._enforce_budget(payload)

    @staticmethod
    def for_salary(twin: Any, target_company: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        ContextBuilder._assert_owner(twin, user_id)
        payload = {
            "skills": [s["n"] for s in ContextBuilder._compact_skills(twin)],
            "experience_years": getattr(twin, "total_years_experience", 0) or 0,
            "current_salary": getattr(twin, "current_salary_lpa", 0.0) or 0.0,
            "target_salary": getattr(twin, "target_salary_lpa", 0.0) or 0.0,
            "location": getattr(twin, "location", "") or "",
            "level": getattr(twin, "career_level", "") or "",
            "target_company": target_company or "",
        }
        return ContextBuilder._enforce_budget(payload)
