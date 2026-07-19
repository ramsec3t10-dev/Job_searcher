"""Phase 7 — curated interview bank: seed-loader idempotency, repository
dedup, subrole inference, and the critical AI-kit fallback when a subrole has
no curated data. Infrastructure only — the JSON below is synthetic test data,
not shipped question content."""
import json
import types

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.domains.catalog import domain_id
from app.interview.subrole import infer_subrole
from app.models.domain_taxonomy import JobDomain
from app.repositories.interview_bank_repository import InterviewBankRepository

# Import the loader module (scripts/ is not a package — load by path).
import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location(
    "seed_interview_bank",
    Path(__file__).resolve().parents[2].parent / "scripts" / "seed_interview_bank.py")
seed_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_loader)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        # A domain must exist for the FK.
        s.add(JobDomain(id=domain_id("software_it"), code="software_it",
                        name="Information Technology", level=0))
        await s.flush()
        yield s
    await engine.dispose()


def _write_bank(tmp_path, n=3):
    data = {
        "domain_code": "software_it",
        "subrole_code": "backend_engineer",
        "questions": [
            {"question_text": f"Q{i}: describe an approach", "category": "technical",
             "difficulty": "mid", "model_answer_guideline": "covers trade-offs",
             "source_type": "curated"}
            for i in range(n)
        ],
    }
    f = tmp_path / "backend_engineer.json"
    f.write_text(json.dumps(data))
    return tmp_path


# ── Subrole inference ───────────────────────────────────────────────────────
def test_infer_subrole():
    assert infer_subrole("Senior Backend Engineer") == "backend_engineer"
    assert infer_subrole("Account Executive") == "account_executive"
    assert infer_subrole("Firmware Engineer - ADAS") == "firmware_engineer"
    assert infer_subrole("") == ""


# ── Repository idempotency ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_bulk_insert_idempotent(db):
    repo = InterviewBankRepository(db)
    rows = [{"domain_id": domain_id("software_it"), "subrole_code": "backend_engineer",
             "question_text": "Explain indexing", "category": "technical",
             "difficulty": "mid"}]
    assert await repo.bulk_insert(rows) == 1
    assert await repo.bulk_insert(rows) == 0          # duplicate skipped
    # Duplicate within a single batch is also collapsed.
    assert await repo.bulk_insert(rows + rows) == 0
    assert await repo.count_for_subrole("backend_engineer") == 1


@pytest.mark.asyncio
async def test_get_by_subrole_filters(db):
    repo = InterviewBankRepository(db)
    await repo.bulk_insert([
        {"domain_id": domain_id("software_it"), "subrole_code": "backend_engineer",
         "question_text": "T1", "category": "technical", "difficulty": "senior"},
        {"domain_id": domain_id("software_it"), "subrole_code": "backend_engineer",
         "question_text": "B1", "category": "behavioral", "difficulty": "mid"},
    ])
    from app.models.interview_bank import QuestionCategory
    tech = await repo.get_by_subrole("backend_engineer", category=QuestionCategory.TECHNICAL)
    assert len(tech) == 1 and tech[0].question_text == "T1"
    assert len(await repo.get_by_subrole("backend_engineer")) == 2
    assert await repo.get_by_subrole("nonexistent_role") == []


# ── Seed-loader idempotency (run twice → no duplicates) ─────────────────────
@pytest.mark.asyncio
async def test_seed_loader_idempotent(db, tmp_path):
    data_dir = _write_bank(tmp_path, n=3)
    s1 = await seed_loader.load_dir(db, data_dir)
    assert s1["added"] == 3
    s2 = await seed_loader.load_dir(db, data_dir)   # re-run
    assert s2["added"] == 0                          # nothing duplicated
    assert await InterviewBankRepository(db).count_for_subrole("backend_engineer") == 3


@pytest.mark.asyncio
async def test_seed_loader_empty_dir(db, tmp_path):
    stats = await seed_loader.load_dir(db, tmp_path)  # no *.json files
    assert stats == {"files": 0, "added": 0, "by_file": {}}


# ── Endpoint fallback: no curated bank → AI kit stands (question_source) ─────
@pytest.mark.asyncio
async def test_curated_overlay_fallback_when_empty(db):
    from app.services.interview_service import InterviewService
    svc = InterviewService(db)
    job = types.SimpleNamespace(title="Backend Engineer")
    overlay = await svc._curated_overlay(job)
    assert overlay["question_source"] == "generated"  # falls back
    assert overlay["curated_questions"] == []
    assert overlay["subrole"] == "backend_engineer"


@pytest.mark.asyncio
async def test_curated_overlay_uses_bank_when_present(db):
    from app.services.interview_service import InterviewService
    await InterviewBankRepository(db).bulk_insert([
        {"domain_id": domain_id("software_it"), "subrole_code": "backend_engineer",
         "question_text": "Explain CAP theorem", "category": "system_design",
         "difficulty": "senior", "model_answer_guideline": "consistency vs availability"},
    ])
    svc = InterviewService(db)
    overlay = await svc._curated_overlay(types.SimpleNamespace(title="Senior Backend Engineer"))
    assert overlay["question_source"] == "curated"
    assert len(overlay["curated_questions"]) == 1
    assert overlay["curated_questions"][0]["category"] == "system_design"
