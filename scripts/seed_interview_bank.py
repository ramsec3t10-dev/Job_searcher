"""EMBEDHUNT AI — Interview bank seed loader (Phase 7).

Loads every ``backend/data/interview_banks/*.json`` file into the
``interview_questions`` table via InterviewBankRepository.bulk_insert, which is
idempotent — safe to re-run repeatedly as more per-subrole tier files are added.

Each file: {"domain_code": "...", "subrole_code": "...", "questions": [ ... ]}.
``domain_code`` must be a seeded JobDomain (run scripts/seed.py first).

Run from the backend/ directory:
    python ../scripts/seed_interview_bank.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.config.settings import settings  # noqa: E402
from app.domains.catalog import domain_id  # noqa: E402
from app.repositories.interview_bank_repository import InterviewBankRepository  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

DATA_DIR = BACKEND / "data" / "interview_banks"


def _load_file(path: Path) -> list[dict]:
    """Parse one subrole file into repository-ready question dicts."""
    doc = json.loads(path.read_text())
    domain_code = doc.get("domain_code", "")
    subrole_code = doc.get("subrole_code", "")
    if not domain_code or not subrole_code:
        raise ValueError(f"{path.name}: missing domain_code/subrole_code")
    did = domain_id(domain_code)
    out: list[dict] = []
    for q in doc.get("questions", []):
        out.append({
            "domain_id": did,
            "subrole_code": subrole_code,
            "question_text": q.get("question_text", ""),
            "category": q.get("category"),
            "difficulty": q.get("difficulty"),
            "model_answer_guideline": q.get("model_answer_guideline"),
            "source_type": q.get("source_type", "curated"),
        })
    return out


async def load_dir(session, data_dir: Path = DATA_DIR) -> dict:
    """Load all *.json files under ``data_dir``. Returns per-file stats."""
    repo = InterviewBankRepository(session)
    stats: dict = {"files": 0, "added": 0, "by_file": {}}
    for path in sorted(data_dir.glob("*.json")):
        questions = _load_file(path)
        added = await repo.bulk_insert(questions)
        stats["files"] += 1
        stats["added"] += added
        stats["by_file"][path.name] = {"parsed": len(questions), "added": added}
    return stats


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        stats = await load_dir(session)
        await session.commit()
    await engine.dispose()
    if stats["files"] == 0:
        print(f"No interview-bank files found in {DATA_DIR} (added in a later phase).")
    else:
        print(f"Interview bank seed complete: {stats['files']} file(s), "
              f"{stats['added']} new question(s).")
        for name, s in stats["by_file"].items():
            print(f"  {name}: parsed {s['parsed']}, added {s['added']}")


if __name__ == "__main__":
    asyncio.run(main())
