from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import JobPosting, SearchHistory, User
from app.schemas.job import JobOut, JobSearchRequest
from app.services.job_scraper import collect_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])

_SORT_COLUMNS = {
    "collected_at": JobPosting.collected_at,
    "date_posted": JobPosting.date_posted,
    "min_amount": JobPosting.min_amount,
    "max_amount": JobPosting.max_amount,
    "title": JobPosting.title,
}


@router.post("/search", response_model=list[JobOut])
def search_jobs(
    payload: JobSearchRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs, failed_sources = collect_jobs(
        db,
        target_role=payload.target_role,
        location=payload.location,
        sources=payload.sources,
        results_wanted=payload.results_wanted,
        job_type=payload.job_type,
        is_remote=payload.is_remote,
        hours_old=payload.hours_old,
        distance=payload.distance,
        easy_apply=payload.easy_apply,
    )

    # Every requested source errored (as opposed to some sources just
    # returning zero results) — that's worth a distinct error rather than a
    # silent empty list, so the caller can tell "nothing matched" apart from
    # "the scrape itself failed".
    if failed_sources and len(failed_sources) == len(payload.sources):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"All job sources failed: {', '.join(failed_sources)}. Try again shortly.",
        )

    if failed_sources:
        # Partial failure: still return the sources that succeeded, but flag
        # which ones didn't via a header instead of changing the response
        # body's shape (kept as list[JobOut] for existing callers).
        response.headers["X-Failed-Sources"] = ", ".join(failed_sources)

    db.add(SearchHistory(
        user_id=current_user.id,
        target_role=payload.target_role,
        source_platforms=", ".join(payload.sources),
        location=payload.location,
        results_count=len(jobs),
    ))
    db.commit()

    return jobs


@router.get("", response_model=list[JobOut])
def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    source: str | None = None,
    location: str | None = None,
    job_type: str | None = None,
    is_remote: bool | None = None,
    min_salary: float | None = None,
    max_salary: float | None = None,
    sort_by: Literal["collected_at", "date_posted", "min_amount", "max_amount", "title"] = "collected_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(JobPosting)

    if q:
        like = f"%{q}%"
        query = query.filter((JobPosting.title.ilike(like)) | (JobPosting.company.ilike(like)))
    if source:
        query = query.filter(JobPosting.source == source)
    if location:
        query = query.filter(JobPosting.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(JobPosting.job_type == job_type)
    if is_remote is not None:
        query = query.filter(JobPosting.is_remote.is_(is_remote))
    if min_salary is not None:
        query = query.filter(JobPosting.max_amount >= min_salary)
    if max_salary is not None:
        query = query.filter(JobPosting.min_amount <= max_salary)

    column = _SORT_COLUMNS[sort_by]
    column = column.desc() if sort_order == "desc" else column.asc()
    # Nulls (e.g. missing date_posted/salary) sort last regardless of direction.
    query = query.order_by(column.nulls_last())

    return query.offset(offset).limit(limit).all()
