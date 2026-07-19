"""EMBEDHUNT AI — Curated interview bank repository (Phase 7)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_bank import (
    InterviewQuestion, QuestionCategory, QuestionDifficulty, QuestionSource,
)


class InterviewBankRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_subrole(
        self, subrole_code: str, *, limit: int = 20,
        category: Optional[QuestionCategory] = None,
        difficulty: Optional[QuestionDifficulty] = None,
    ) -> list[InterviewQuestion]:
        stmt = select(InterviewQuestion).where(
            InterviewQuestion.subrole_code == subrole_code)
        if category is not None:
            stmt = stmt.where(InterviewQuestion.category == category)
        if difficulty is not None:
            stmt = stmt.where(InterviewQuestion.difficulty == difficulty)
        stmt = stmt.order_by(InterviewQuestion.difficulty,
                             InterviewQuestion.category).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def count_for_subrole(self, subrole_code: str) -> int:
        res = await self.db.execute(
            select(InterviewQuestion.id).where(
                InterviewQuestion.subrole_code == subrole_code))
        return len(list(res.scalars().all()))

    async def bulk_insert(self, questions: list[dict]) -> int:
        """Idempotent insert. Skips any (subrole_code, question_text) that already
        exists so re-seeding never duplicates. Returns the count actually added."""
        if not questions:
            return 0
        subroles = {q.get("subrole_code", "") for q in questions}
        existing_res = await self.db.execute(
            select(InterviewQuestion.subrole_code, InterviewQuestion.question_text)
            .where(InterviewQuestion.subrole_code.in_(subroles)))
        existing = {(sr, txt) for sr, txt in existing_res.all()}

        added = 0
        seen_in_batch: set[tuple[str, str]] = set()
        for q in questions:
            sr = q.get("subrole_code", "")
            txt = (q.get("question_text") or "").strip()
            if not sr or not txt:
                continue
            key = (sr, txt)
            if key in existing or key in seen_in_batch:
                continue
            seen_in_batch.add(key)
            self.db.add(InterviewQuestion(
                domain_id=q["domain_id"],
                subrole_code=sr,
                question_text=txt,
                category=QuestionCategory(q["category"]),
                difficulty=QuestionDifficulty(q["difficulty"]),
                model_answer_guideline=q.get("model_answer_guideline"),
                source_type=QuestionSource(q.get("source_type", "curated")),
            ))
            added += 1
        if added:
            await self.db.flush()
        return added
