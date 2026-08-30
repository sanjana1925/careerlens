import io

from app.database import SessionLocal
from app.models import JobPosting


def _seed_job(title="Backend Engineer", description="Python and Docker role", url="https://x/job-1"):
    session = SessionLocal()
    try:
        posting = JobPosting(title=title, company="Acme", location="Remote", source="linkedin", url=url, description=description)
        session.add(posting)
        session.commit()
        session.refresh(posting)
        return posting.id
    finally:
        session.close()


def _upload_resume(client, auth_headers, text="Python and Docker developer."):
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", io.BytesIO(text.encode()), "text/plain")},
    )
    return resp.json()["id"]


def test_match_jobs_scores_against_collected_jobs(client, auth_headers):
    _seed_job(title="Great Fit", description="Needs Python and Docker skills.", url="https://x/great")
    _seed_job(title="Poor Fit", description="Needs Rust and Kubernetes skills.", url="https://x/poor")
    resume_id = _upload_resume(client, auth_headers, "Python and Docker developer.")

    resp = client.post("/api/match", headers=auth_headers, json={"resume_id": resume_id})

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    # best match sorts first
    assert results[0]["match_score"] >= results[1]["match_score"]


def test_match_jobs_resume_not_found_returns_404(client, auth_headers):
    resp = client.post("/api/match", headers=auth_headers, json={"resume_id": 999999})
    assert resp.status_code == 404


def test_save_match_marks_is_saved(client, auth_headers):
    _seed_job()
    resume_id = _upload_resume(client, auth_headers)
    match_id = client.post("/api/match", headers=auth_headers, json={"resume_id": resume_id}).json()[0]["id"]

    resp = client.post(f"/api/match/{match_id}/save", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["is_saved"] is True


def test_save_match_not_found_returns_404(client, auth_headers):
    resp = client.post("/api/match/999999/save", headers=auth_headers)
    assert resp.status_code == 404


def test_list_saved_matches_only_returns_saved(client, auth_headers):
    _seed_job()
    resume_id = _upload_resume(client, auth_headers)
    match_id = client.post("/api/match", headers=auth_headers, json={"resume_id": resume_id}).json()[0]["id"]

    assert client.get("/api/match/saved", headers=auth_headers).json() == []

    client.post(f"/api/match/{match_id}/save", headers=auth_headers)
    saved = client.get("/api/match/saved", headers=auth_headers).json()
    assert len(saved) == 1


def test_list_saved_matches_supports_pagination(client, auth_headers):
    for i in range(3):
        _seed_job(title=f"Job {i}", url=f"https://x/pag-{i}")
    resume_id = _upload_resume(client, auth_headers)
    results = client.post("/api/match", headers=auth_headers, json={"resume_id": resume_id}).json()
    for match in results:
        client.post(f"/api/match/{match['id']}/save", headers=auth_headers)

    page = client.get("/api/match/saved", params={"limit": 2, "offset": 0}, headers=auth_headers).json()
    assert len(page) == 2


def test_market_intelligence_returns_skill_demand_for_matching_titles(client, auth_headers):
    _seed_job(title="Python Backend Engineer", description="Needs Python and Docker.", url="https://x/pbe")
    _seed_job(title="Frontend Engineer", description="Needs React.", url="https://x/fe")

    resp = client.get(
        "/api/match/market-intelligence",
        headers=auth_headers,
        params={"target_role": "Backend"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["jobs_analyzed"] == 1
    skills = {s["skill"] for s in body["top_skills"]}
    assert "python" in skills
