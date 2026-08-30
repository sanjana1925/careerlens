import pytest

from app.database import SessionLocal
from app.services import job_scraper


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class _FakeDataFrame:
    def __init__(self, records):
        self._records = records
        self.empty = len(records) == 0

    def to_dict(self, orient="records"):
        return self._records


def test_scrape_jobs_isolates_a_failing_source_and_keeps_the_rest(monkeypatch):
    def fake_scrape(site_name, **kwargs):
        source = site_name[0]
        if source == "indeed":
            raise RuntimeError("indeed is rate-limiting us")
        return _FakeDataFrame([{"title": "Engineer", "site": source, "job_url": f"https://x/{source}"}])

    monkeypatch.setattr("jobspy.scrape_jobs", fake_scrape)

    records, failed_sources = job_scraper.scrape_jobs(
        target_role="Engineer", location=None, sources=["linkedin", "indeed", "glassdoor"], results_wanted=5,
    )

    assert failed_sources == ["indeed"]
    assert {r["site"] for r in records} == {"linkedin", "glassdoor"}


def test_scrape_jobs_all_sources_failing_returns_empty_records(monkeypatch):
    def fake_scrape(site_name, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("jobspy.scrape_jobs", fake_scrape)

    records, failed_sources = job_scraper.scrape_jobs(
        target_role="Engineer", location=None, sources=["linkedin", "indeed"], results_wanted=5,
    )

    assert records == []
    assert failed_sources == ["linkedin", "indeed"]


def test_clean_and_dedupe_drops_rows_without_url():
    raw = [
        {"title": "Engineer", "site": "linkedin", "job_url": "", "company": "Acme"},
        {"title": "Engineer 2", "site": "linkedin", "job_url": "https://x/2", "company": "Acme"},
    ]
    cleaned = job_scraper.clean_and_dedupe(raw)
    assert len(cleaned) == 1
    assert cleaned[0]["url"] == "https://x/2"


def test_clean_and_dedupe_dedupes_by_source_and_url():
    raw = [
        {"title": "Engineer", "site": "linkedin", "job_url": "https://x/1", "company": "Acme"},
        {"title": "Engineer (dup)", "site": "linkedin", "job_url": "https://x/1", "company": "Acme"},
        {"title": "Engineer", "site": "indeed", "job_url": "https://x/1", "company": "Acme"},
    ]
    cleaned = job_scraper.clean_and_dedupe(raw)
    assert len(cleaned) == 2  # same URL from two different sources is not a dupe


def test_clean_and_dedupe_normalizes_nan_like_values_to_none():
    raw = [{"title": "Engineer", "site": "linkedin", "job_url": "https://x/1", "company": float("nan")}]
    cleaned = job_scraper.clean_and_dedupe(raw)
    assert cleaned[0]["company"] is None


def test_persist_jobs_inserts_new_postings(db_session):
    cleaned = [{
        "title": "Engineer", "company": "Acme", "location": "Remote", "source": "linkedin",
        "url": "https://x/1", "description": "Python role", "min_amount": 100000.0,
        "max_amount": 150000.0, "job_type": "fulltime", "is_remote": True, "date_posted": None,
    }]

    saved = job_scraper.persist_jobs(db_session, cleaned)

    assert len(saved) == 1
    assert saved[0].id is not None
    assert saved[0].title == "Engineer"


def test_persist_jobs_upserts_existing_by_source_and_url(db_session):
    first = [{
        "title": "Engineer", "company": "Acme", "location": "Remote", "source": "linkedin",
        "url": "https://x/1", "description": "", "min_amount": None, "max_amount": None,
        "job_type": None, "is_remote": None, "date_posted": None,
    }]
    job_scraper.persist_jobs(db_session, first)

    second = [{
        "title": "Engineer", "company": "Acme", "location": "Remote", "source": "linkedin",
        "url": "https://x/1", "description": "Backfilled description", "min_amount": None,
        "max_amount": None, "job_type": "fulltime", "is_remote": True, "date_posted": None,
    }]
    saved = job_scraper.persist_jobs(db_session, second)

    assert len(saved) == 1
    assert saved[0].description == "Backfilled description"
    assert saved[0].job_type == "fulltime"
    assert saved[0].is_remote is True


def test_persist_jobs_does_not_overwrite_existing_description(db_session):
    first = [{
        "title": "Engineer", "company": "Acme", "location": "Remote", "source": "linkedin",
        "url": "https://x/1", "description": "Original description", "min_amount": None,
        "max_amount": None, "job_type": None, "is_remote": None, "date_posted": None,
    }]
    job_scraper.persist_jobs(db_session, first)

    second = dict(first[0])
    second["description"] = "Different description"
    saved = job_scraper.persist_jobs(db_session, [second])

    assert saved[0].description == "Original description"
