"""EMBEDHUNT AI — Live job pipeline.

Runs discovery across all configured sources, persists new/updated postings into
``discovered_jobs`` (idempotent upsert keyed on source posting id), and reports
run statistics. Failures in any single source are isolated by the aggregator, so
the pipeline always makes progress and degrades gracefully.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.job_sources.aggregator import discover
from app.job_sources.base import Fetcher, JobSource
from app.job_sources.domain_classifier import DomainClassifier
from app.repositories.discovered_job_repository import DiscoveredJobRepository

logger = logging.getLogger("embedhunt.discovery")


@dataclass
class PipelineStats:
    discovered: int = 0
    created: int = 0
    updated: int = 0
    sources_ok: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "discovered": self.discovered,
            "created": self.created,
            "updated": self.updated,
            "sources_ok": self.sources_ok,
            "sources_failed": self.sources_failed,
        }


class JobPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DiscoveredJobRepository(db)

    async def run(self, *, fetcher: Fetcher | None = None,
                  sources: list[JobSource] | None = None,
                  classifier: DomainClassifier | None = None,
                  user_id: str | None = None,
                  limit_per_source: int = 100) -> PipelineStats:
        discovery = discover(sources=sources, fetcher=fetcher,
                             limit_per_source=limit_per_source)
        # Rule-only classifier by default → no network in the common path/tests.
        # Callers wanting the LLM tier inject a classifier built with a router.
        classifier = classifier or DomainClassifier()
        stats = PipelineStats(
            sources_ok=list(discovery.sources_ok),
            sources_failed=list(discovery.sources_failed),
        )
        for posting in discovery.postings:
            # Domain-tag every posting before persistence (never let a
            # classification error abort ingestion).
            try:
                result = await classifier.classify(
                    posting.title, posting.description, user_id=user_id, db=self.db)
                posting.domain_id = result.domain_id
            except Exception as exc:  # noqa: BLE001
                logger.warning("classify_failed %s (%s)", posting.title, exc)
            _, created = await self.repo.upsert(posting.to_corpus_dict())
            stats.discovered += 1
            if created:
                stats.created += 1
            else:
                stats.updated += 1
        return stats


async def run_pipeline(db: AsyncSession, *, fetcher: Fetcher | None = None,
                       sources: list[JobSource] | None = None,
                       classifier: DomainClassifier | None = None) -> PipelineStats:
    return await JobPipeline(db).run(fetcher=fetcher, sources=sources,
                                     classifier=classifier)
