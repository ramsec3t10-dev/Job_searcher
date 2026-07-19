"""Phase 1 — domain taxonomy: migration, backfill, and repository tests.

Runs the real Alembic chain on a throwaway SQLite file so we exercise the
actual migration (not a hand-rolled schema), including the data backfill that
copies embedded columns into domain_profile_data.
"""
import sqlite3
import uuid

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.settings import settings
from app.domains.catalog import DOMAINS, EMBEDDED_CATEGORIES, domain_id
from app.repositories.domain_repository import DomainRepository


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    return cfg


def _seed_pre_migration_rows(db_path: str) -> str:
    """Insert one embedded candidate_profile (pre-Phase-1 shape) + one job."""
    cid = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO candidate_profiles (id, user_id, headline, total_experience_years, "
        "embedded_domain_score, profile_score, is_actively_looking, min_salary_lpa, "
        "notice_period_days, total_recommendations, total_applications, interview_rate, "
        "offer_rate, created_at, updated_at) VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))",
        (cid, str(uuid.uuid4()), "Embedded Engineer", 5.0, 77, 80, 1, 15.0, 60, 0, 0, 0.0, 0.0),
    )
    conn.execute(
        "INSERT INTO discovered_jobs (id, external_ref, dedup_key, title, company, "
        "created_at, updated_at) VALUES (?,?,?,?,?,datetime('now'),datetime('now'))",
        (str(uuid.uuid4()), "greenhouse:1", "k1", "Firmware Engineer", "Acme"),
    )
    conn.commit()
    conn.close()
    return cid


@pytest.fixture
def migrated_db(tmp_path, monkeypatch):
    """Upgrade to just-before Phase 1, seed real rows, then upgrade to head."""
    db_file = tmp_path / "phase1.db"
    url = f"sqlite+aiosqlite:///{db_file}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    cfg = _alembic_cfg()

    command.upgrade(cfg, "a1b2c3d4e5f6")           # state before Phase 1
    cid = _seed_pre_migration_rows(str(db_file))
    command.upgrade(cfg, "b2c3d4e5f6a7")            # Phase 1 only (isolated)
    return {"path": str(db_file), "url": url, "profile_id": cid}


def test_migration_creates_taxonomy_and_backfills(migrated_db):
    conn = sqlite3.connect(migrated_db["path"])

    # All domains seeded and active.
    assert conn.execute("SELECT count(*) FROM job_domains").fetchone()[0] == len(DOMAINS)
    assert conn.execute(
        "SELECT count(*) FROM job_domains WHERE is_active=1").fetchone()[0] == len(DOMAINS)

    # Embedded skill categories migrated verbatim from the matcher weights.
    cats = dict(conn.execute("SELECT code, weight FROM skill_categories").fetchall())
    assert cats == {code: w for code, _n, w in EMBEDDED_CATEGORIES}

    emb = domain_id("embedded_engineering")

    # Existing job backfilled to embedded_engineering.
    assert conn.execute(
        "SELECT domain_id FROM discovered_jobs").fetchone()[0] == emb

    # Existing profile: primary domain set AND embedded score preserved in BOTH
    # the original column and domain_profile_data (old + new stay consistent).
    row = conn.execute(
        "SELECT primary_domain_id, embedded_domain_score, domain_profile_data "
        "FROM candidate_profiles WHERE id=?", (migrated_db["profile_id"],)).fetchone()
    assert row[0] == emb
    assert row[1] == 77                                    # old column untouched
    import json
    dpd = json.loads(row[2])
    assert dpd["embedded_engineering"]["embedded_domain_score"] == 77
    conn.close()


def test_downgrade_is_clean(migrated_db, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", migrated_db["url"])
    cfg = _alembic_cfg()
    command.downgrade(cfg, "a1b2c3d4e5f6")   # must not raise
    conn = sqlite3.connect(migrated_db["path"])
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "job_domains" not in tables
    cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_profiles)").fetchall()}
    assert "domain_profile_data" not in cols
    assert "embedded_domain_score" in cols   # original column survives downgrade
    conn.close()


@pytest.fixture
def head_db(tmp_path, monkeypatch):
    """Full-schema DB migrated to head (sync — env.py drives its own loop)."""
    db_file = tmp_path / "repo.db"
    url = f"sqlite+aiosqlite:///{db_file}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    command.upgrade(_alembic_cfg(), "head")
    return url


@pytest_asyncio.fixture
async def repo_session(head_db):
    engine = create_async_engine(head_db)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_reads(repo_session):
    from app.domains.catalog import flatten, top_level_domains
    repo = DomainRepository(repo_session)

    # Whole hierarchy present and active; embedded reparented under IT.
    active = await repo.list_active_domains()
    assert len(active) == len(flatten())

    emb = await repo.get_by_code("embedded_engineering")
    assert emb is not None and emb.level == 1 and emb.parent_id is not None

    it = await repo.get_by_code("software_it")
    assert it is not None and it.level == 0 and emb.parent_id == it.id

    # Embedded keeps its migrated skill categories, ordered by weight desc.
    cats = await repo.get_skill_categories(emb.id)
    assert {c.code for c in cats} == {code for code, _n, _w in EMBEDDED_CATEGORIES}
    assert cats[0].weight >= cats[-1].weight

    assert await repo.get_by_code("nonexistent") is None
    # Sub-domains exist under IT (level 1).
    it_cats = [d for d in active if d.parent_id == it.id]
    assert len(it_cats) >= 10
