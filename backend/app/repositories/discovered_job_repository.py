"""EMBEDHUNT AI — Discovered Job Repository."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.base_repository import BaseRepository
from app.models.discovered_job import DiscoveredJob

_CORPUS_FIELDS = (
    "title", "company", "company_tier", "location", "source_portal",
    "source_url", "apply_url", "description", "required_skills",
    "experience_min", "experience_max", "salary_min_lpa", "salary_max_lpa",
    "domain_id", "industry",
)


class DiscoveredJobRepository(BaseRepository[DiscoveredJob]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, DiscoveredJob)

    async def get_by_external_ref(self, external_ref: str) -> Optional[DiscoveredJob]:
        r = await self.db.execute(
            select(DiscoveredJob).where(DiscoveredJob.external_ref == external_ref))
        return r.scalar_one_or_none()

    async def upsert(self, corpus: dict) -> tuple[DiscoveredJob, bool]:
        """Insert or update a posting keyed by its corpus ``id``. Returns (job, created)."""
        external_ref = corpus.get("id", "")
        dedup_key = f"{corpus.get('company', '').lower()}::{corpus.get('title', '').lower()}"
        now = datetime.now(timezone.utc)
        existing = await self.get_by_external_ref(external_ref)
        if existing is not None:
            for f in _CORPUS_FIELDS:
                if f in corpus:
                    setattr(existing, f, corpus[f])
            existing.dedup_key = dedup_key
            existing.is_active = True
            existing.last_seen_at = now
            await self.db.flush()
            return existing, False
        data = {f: corpus.get(f) for f in _CORPUS_FIELDS}
        obj = DiscoveredJob(external_ref=external_ref, dedup_key=dedup_key,
                            is_active=True, last_seen_at=now, **data)
        self.db.add(obj)
        await self.db.flush()
        return obj, True

    async def get_active_corpus(self, limit: int = 500) -> list[dict]:
        r = await self.db.execute(
            select(DiscoveredJob).where(DiscoveredJob.is_active.is_(True)).limit(limit))
        return [j.to_corpus_dict() for j in r.scalars().all()]

    async def count_active(self) -> int:
        r = await self.db.execute(select(DiscoveredJob).where(DiscoveredJob.is_active.is_(True)))
        return len(list(r.scalars().all()))
