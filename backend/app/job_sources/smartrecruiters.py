"""EMBEDHUNT AI — SmartRecruiters connector.

Consumes the **public** SmartRecruiters Posting API that companies expose to
render their own career pages:

    https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100

Unlike the developer-centric ATSs (Greenhouse/Lever skew tech), SmartRecruiters
hosts a broad cross-industry mix — retail, hospitality, healthcare, sales,
finance, operations — which makes it a strong source for multi-domain coverage.
It also returns a per-posting ``industry`` label, populated here independently of
the domain classifier. HTTP stays behind the injected ``fetcher`` for testing.
"""
from __future__ import annotations

from app.job_sources.base import Fetcher, JobSource
from app.job_sources.schema import JobPosting

_API = "https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100"
_JOB_URL = "https://jobs.smartrecruiters.com/{company}/{posting_id}"


def _location(loc: dict) -> str:
    if not isinstance(loc, dict):
        return ""
    if loc.get("remote"):
        return "Remote"
    parts = [loc.get("city"), loc.get("region"), loc.get("country")]
    return ", ".join(p for p in parts if p)


def _label(value) -> str:
    """SmartRecruiters wraps taxonomies as {id, label}; pull the label."""
    if isinstance(value, dict):
        return value.get("label", "") or ""
    return str(value or "")


class SmartRecruitersSource(JobSource):
    def __init__(self, company_id: str, company: str, company_tier: str = "other") -> None:
        self.company_id = company_id
        self.company = company
        self.company_tier = company_tier
        self.name = f"smartrecruiters:{company_id}"

    def fetch(self, fetcher: Fetcher) -> list[JobPosting]:
        data = fetcher(_API.format(company=self.company_id))
        rows = data.get("content", []) if isinstance(data, dict) else []
        postings: list[JobPosting] = []
        for job in rows:
            if not isinstance(job, dict):
                continue
            posting_id = str(job.get("id", ""))
            title = job.get("name", "") or job.get("title", "")
            industry = _label(job.get("industry"))
            department = _label(job.get("department"))
            function = _label(job.get("function"))
            # The list endpoint omits the full ad body; synthesise a rich-enough
            # description from the structured fields so classification/skill
            # extraction have signal without a second per-posting request.
            ad = job.get("jobAd") or {}
            body = ""
            if isinstance(ad, dict):
                sections = ad.get("sections") or {}
                jd = sections.get("jobDescription") if isinstance(sections, dict) else None
                if isinstance(jd, dict):
                    body = jd.get("text", "") or ""
            description = body or " ".join(
                p for p in (title, function, department, industry) if p)
            apply_url = job.get("applyUrl") or _JOB_URL.format(
                company=self.company_id, posting_id=posting_id)
            postings.append(
                JobPosting(
                    external_id=posting_id,
                    title=title,
                    company=self.company,
                    location=_location(job.get("location")),
                    apply_url=apply_url,
                    description=description,
                    source_portal=self.name,
                    source_url=apply_url,
                    company_tier=self.company_tier,
                    industry=industry or None,
                )
            )
        return postings
