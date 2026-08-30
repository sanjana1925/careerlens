"""Multi-platform job collection via JobSpy, with cleaning/dedup and DB persistence."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import JobPosting
from app.services import vector_store

logger = logging.getLogger(__name__)

# Sites the pinned python-jobspy==1.1.75 actually supports (its own JobSpy.Site
# enum). Naukri is NOT in this list despite being mentioned in early project
# notes — passing it crashes the underlying scrape with a raw KeyError, so we
# validate against this set before ever calling into JobSpy.
SUPPORTED_SOURCES = {"linkedin", "indeed", "glassdoor", "google", "zip_recruiter"}


def _clean_scalar(value):
    """JobSpy returns pandas-native NaN/NaT for missing fields (common for
    LinkedIn results, e.g. no posted date) instead of None. Neither is a
    valid SQLite DateTime/Float parameter nor valid JSON, so normalize to
    None here rather than at every call site. `value != value` is true for
    both NaN and NaT without importing pandas/math just for this check.
    """
    return None if value != value else value


def scrape_jobs(
    target_role: str,
    location: str | None,
    sources: list[str],
    results_wanted: int,
    job_type: str | None = None,
    is_remote: bool | None = None,
    hours_old: int | None = None,
    distance: int | None = None,
    easy_apply: bool | None = None,
) -> tuple[list[dict], list[str]]:
    """Calls JobSpy once per source and returns (records, failed_sources).

    Each source is isolated in its own try/except: JobSpy's own multi-site
    call has no per-site error isolation, so one flaky source (site layout
    change, rate-limiting, CAPTCHA, network blip) previously took down the
    whole request with a 500 even when the other sources would have
    succeeded. A source that raises is recorded in `failed_sources` and
    skipped rather than aborting the others.

    Import is deferred so the rest of the app works even before `python-jobspy`
    (and its heavier scraping dependencies) is installed.
    """
    from jobspy import scrape_jobs as _scrape_jobs

    records: list[dict] = []
    failed_sources: list[str] = []

    for source in sources:
        # linkedin_fetch_description=True makes JobSpy issue one extra request
        # per LinkedIn result to fetch its full description. Without it,
        # LinkedIn rows come back with an empty description, which zeroes out
        # skill-gap/match scoring for every LinkedIn job downstream
        # (extract_skills("") == set()).
        kwargs = dict(
            site_name=[source],
            search_term=target_role,
            location=location,
            results_wanted=results_wanted,
            linkedin_fetch_description=True,
            job_type=job_type,
            easy_apply=easy_apply,
        )
        if is_remote is not None:
            kwargs["is_remote"] = is_remote
        if hours_old is not None:
            kwargs["hours_old"] = hours_old
        if distance is not None:
            kwargs["distance"] = distance

        try:
            df = _scrape_jobs(**kwargs)
        except Exception:
            logger.warning("JobSpy scrape failed for source %r, skipping", source, exc_info=True)
            failed_sources.append(source)
            continue

        if df is not None and not df.empty:
            records.extend(df.to_dict(orient="records"))

    return records, failed_sources


def clean_and_dedupe(raw_jobs: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    cleaned = []

    for job in raw_jobs:
        source = str(job.get("site", "")).strip().lower()
        url = str(job.get("job_url", "")).strip()
        if not url or (source, url) in seen:
            continue
        seen.add((source, url))

        cleaned.append({
            "title": str(job.get("title", "")).strip(),
            "company": _clean_scalar(job.get("company")),
            "location": _clean_scalar(job.get("location")),
            "source": source,
            "url": url,
            "description": _clean_scalar(job.get("description")) or "",
            "min_amount": _clean_scalar(job.get("min_amount")),
            "max_amount": _clean_scalar(job.get("max_amount")),
            "job_type": _clean_scalar(job.get("job_type")) or None,
            "is_remote": _clean_scalar(job.get("is_remote")),
            "date_posted": _clean_scalar(job.get("date_posted")),
        })

    return cleaned


def persist_jobs(db: Session, jobs: list[dict]) -> list[JobPosting]:
    """Upserts jobs by (source, url) and returns the resulting JobPosting rows."""
    saved: list[JobPosting] = []

    for job in jobs:
        existing = (
            db.query(JobPosting)
            .filter(JobPosting.source == job["source"], JobPosting.url == job["url"])
            .first()
        )
        if existing:
            # Backfill rows saved before linkedin_fetch_description was turned
            # on (or from a run that otherwise came back without a
            # description) instead of leaving them permanently empty.
            if not existing.description and job.get("description"):
                existing.description = job["description"]
            if existing.job_type is None and job.get("job_type"):
                existing.job_type = job["job_type"]
            if existing.is_remote is None and job.get("is_remote") is not None:
                existing.is_remote = job["is_remote"]
            saved.append(existing)
            continue

        date_posted = job.get("date_posted")
        if isinstance(date_posted, str):
            try:
                date_posted = datetime.fromisoformat(date_posted)
            except ValueError:
                date_posted = None

        posting = JobPosting(
            title=job["title"],
            company=job.get("company"),
            location=job.get("location"),
            source=job["source"],
            url=job["url"],
            description=job.get("description") or "",
            min_amount=job.get("min_amount"),
            max_amount=job.get("max_amount"),
            job_type=job.get("job_type"),
            is_remote=job.get("is_remote"),
            date_posted=date_posted,
        )
        db.add(posting)
        saved.append(posting)

    db.commit()
    for posting in saved:
        db.refresh(posting)

    vector_store.index_jobs(saved)

    return saved


def collect_jobs(
    db: Session,
    target_role: str,
    location: str | None,
    sources: list[str],
    results_wanted: int,
    job_type: str | None = None,
    is_remote: bool | None = None,
    hours_old: int | None = None,
    distance: int | None = None,
    easy_apply: bool | None = None,
) -> tuple[list[JobPosting], list[str]]:
    """Returns (postings, failed_sources) — failed_sources is non-empty only
    when at least one requested source errored (see scrape_jobs)."""
    raw, failed_sources = scrape_jobs(
        target_role,
        location,
        sources,
        results_wanted,
        job_type=job_type,
        is_remote=is_remote,
        hours_old=hours_old,
        distance=distance,
        easy_apply=easy_apply,
    )
    cleaned = clean_and_dedupe(raw)
    return persist_jobs(db, cleaned), failed_sources
