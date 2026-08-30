from datetime import datetime

from pydantic import BaseModel, field_validator

from app.services.job_scraper import SUPPORTED_SOURCES

# JobSpy's JobType enum values (app/services/job_scraper.py's scrape_jobs passes
# this straight through) — kept here too so the API rejects typos up front
# instead of silently reaching JobSpy with a value it can't resolve.
SUPPORTED_JOB_TYPES = {"fulltime", "parttime", "internship", "contract"}


class JobSearchRequest(BaseModel):
    target_role: str
    location: str | None = None
    sources: list[str] = ["linkedin", "indeed", "glassdoor", "google"]
    results_wanted: int = 20

    # Advanced filters, passed through to JobSpy at scrape time.
    job_type: str | None = None
    is_remote: bool | None = None
    hours_old: int | None = None  # only return postings within the last N hours
    distance: int | None = None  # miles from `location`
    easy_apply: bool | None = None

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, sources: list[str]) -> list[str]:
        unsupported = sorted(set(sources) - SUPPORTED_SOURCES)
        if unsupported:
            raise ValueError(
                f"Unsupported job source(s): {', '.join(unsupported)}. "
                f"Supported: {', '.join(sorted(SUPPORTED_SOURCES))}."
            )
        return sources

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, job_type: str | None) -> str | None:
        if job_type is not None and job_type not in SUPPORTED_JOB_TYPES:
            raise ValueError(
                f"Unsupported job_type '{job_type}'. Supported: {', '.join(sorted(SUPPORTED_JOB_TYPES))}."
            )
        return job_type


class JobOut(BaseModel):
    id: int
    title: str
    company: str | None
    location: str | None
    source: str
    url: str
    min_amount: float | None
    max_amount: float | None
    job_type: str | None
    is_remote: bool | None
    date_posted: datetime | None
    collected_at: datetime

    model_config = {"from_attributes": True}
