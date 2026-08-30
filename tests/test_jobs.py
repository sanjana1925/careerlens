from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import JobPosting


def _seed_job(**overrides):
    defaults = dict(
        title="Backend Engineer", company="Acme", location="Remote", source="linkedin",
        url=f"https://x/{overrides.get('title', 'job')}-{id(overrides)}", description="Python and Docker role",
        min_amount=100000.0, max_amount=140000.0, job_type="fulltime", is_remote=True,
        date_posted=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    session = SessionLocal()
    try:
        posting = JobPosting(**defaults)
        session.add(posting)
        session.commit()
        session.refresh(posting)
        return posting.id
    finally:
        session.close()


def test_list_jobs_requires_auth(client):
    assert client.get("/api/jobs").status_code == 401


def test_list_jobs_returns_seeded_postings(client, auth_headers):
    _seed_job(title="Backend Engineer")
    _seed_job(title="Frontend Engineer", url="https://x/frontend-1")

    resp = client.get("/api/jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_jobs_supports_pagination(client, auth_headers):
    _seed_job(title="Job A", url="https://x/a")
    _seed_job(title="Job B", url="https://x/b")
    _seed_job(title="Job C", url="https://x/c")

    page1 = client.get("/api/jobs", params={"limit": 2, "offset": 0, "sort_by": "title", "sort_order": "asc"}, headers=auth_headers).json()
    page2 = client.get("/api/jobs", params={"limit": 2, "offset": 2, "sort_by": "title", "sort_order": "asc"}, headers=auth_headers).json()

    assert [j["title"] for j in page1] == ["Job A", "Job B"]
    assert [j["title"] for j in page2] == ["Job C"]


def test_list_jobs_rejects_limit_above_cap(client, auth_headers):
    resp = client.get("/api/jobs", params={"limit": 500}, headers=auth_headers)
    assert resp.status_code == 422


def test_list_jobs_filters_by_query_text(client, auth_headers):
    _seed_job(title="Backend Engineer", url="https://x/be-1")
    _seed_job(title="Frontend Engineer", url="https://x/fe-1")

    resp = client.get("/api/jobs", params={"q": "Frontend"}, headers=auth_headers)
    titles = [j["title"] for j in resp.json()]
    assert titles == ["Frontend Engineer"]


def test_list_jobs_filters_by_salary_range(client, auth_headers):
    _seed_job(title="Low Salary", url="https://x/low", min_amount=50000.0, max_amount=60000.0)
    _seed_job(title="High Salary", url="https://x/high", min_amount=150000.0, max_amount=180000.0)

    resp = client.get("/api/jobs", params={"min_salary": 100000}, headers=auth_headers)
    titles = [j["title"] for j in resp.json()]
    assert titles == ["High Salary"]


def test_list_jobs_sorts_by_title_ascending(client, auth_headers):
    _seed_job(title="Zebra Role", url="https://x/z")
    _seed_job(title="Alpha Role", url="https://x/a")

    resp = client.get("/api/jobs", params={"sort_by": "title", "sort_order": "asc"}, headers=auth_headers)
    titles = [j["title"] for j in resp.json()]
    assert titles == ["Alpha Role", "Zebra Role"]


def test_search_jobs_persists_results_and_records_history(client, auth_headers, monkeypatch):
    def fake_collect_jobs(db, target_role, location, sources, results_wanted, **kwargs):
        posting = JobPosting(
            title="Fake Search Result", company="Acme", location=location, source=sources[0],
            url="https://x/fake-search-1", description="Python role",
        )
        db.add(posting)
        db.commit()
        db.refresh(posting)
        return [posting], []

    monkeypatch.setattr("app.routers.jobs.collect_jobs", fake_collect_jobs)

    resp = client.post(
        "/api/jobs/search",
        headers=auth_headers,
        json={"target_role": "Software Engineer", "sources": ["linkedin"], "results_wanted": 5},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Fake Search Result"
    assert "X-Failed-Sources" not in resp.headers


def test_search_jobs_rejects_unsupported_source(client, auth_headers):
    resp = client.post(
        "/api/jobs/search",
        headers=auth_headers,
        json={"target_role": "Software Engineer", "sources": ["naukri"]},
    )
    assert resp.status_code == 422


def test_search_jobs_partial_source_failure_still_returns_successful_results(client, auth_headers, monkeypatch):
    def fake_collect_jobs(db, target_role, location, sources, results_wanted, **kwargs):
        posting = JobPosting(
            title="Only LinkedIn Result", company="Acme", location=location, source="linkedin",
            url="https://x/partial-1", description="Python role",
        )
        db.add(posting)
        db.commit()
        db.refresh(posting)
        return [posting], ["indeed"]

    monkeypatch.setattr("app.routers.jobs.collect_jobs", fake_collect_jobs)

    resp = client.post(
        "/api/jobs/search",
        headers=auth_headers,
        json={"target_role": "Software Engineer", "sources": ["linkedin", "indeed"], "results_wanted": 5},
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.headers["X-Failed-Sources"] == "indeed"


def test_search_jobs_all_sources_failing_returns_502(client, auth_headers, monkeypatch):
    def fake_collect_jobs(db, target_role, location, sources, results_wanted, **kwargs):
        return [], list(sources)

    monkeypatch.setattr("app.routers.jobs.collect_jobs", fake_collect_jobs)

    resp = client.post(
        "/api/jobs/search",
        headers=auth_headers,
        json={"target_role": "Software Engineer", "sources": ["linkedin", "indeed"], "results_wanted": 5},
    )

    assert resp.status_code == 502
